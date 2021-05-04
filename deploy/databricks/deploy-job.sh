#!/bin/sh

#################################################################################################################
# Deploying to databricks involves 3 steps:
#
# 1. List existing jobs and find the job id with cluster name
#
# 2. Decide next step based on number of jobs found
# - If job doesn't exist, then create job
# - If one job exists, then reset job
# - If more than one job exists, then fail (this should never happen)
#
# 3. Run new job
#
# For details, see https://docs.databricks.com/dev-tools/api/latest/jobs.html
#################################################################################################################

DATABRICKS_WORKSPACE="https://<company-name>.cloud.databricks.com"
ECR_IMAGE_URL="<aws-account>.dkr.ecr.<aws-region>.amazonaws.com/<image-name>"
INSTANCE_PROFILE_ARN = "arn:aws:iam::<aws-account>:instance-profile/<profile-name>"

job_settings='{
  "name": "'"$CLUSTER_NAME"'",
  "new_cluster": {
    "spark_version": "'"$SPARK_VERSION"'",
    "node_type_id": "'"$INSTANCE_TYPE"'",
    "driver_node_type_id": "'"$INSTANCE_TYPE"'",
    "autoscale": {
      "min_workers": '"$MIN_WORKERS"',
      "max_workers": '"$MAX_WORKERS"'
    },
    "docker_image": {
      "url": "'"$ECR_IMAGE_URL"'"
    },
    "aws_attributes": {
      "first_on_demand": 1,
      "availability": "SPOT_WITH_FALLBACK",
      "zone_id": "us-east-1b",
      "spot_bid_price_percent": 100,
      "instance_profile_arn": ""'$INSTANCE_PROFILE_ARN'"",
      "ebs_volume_type": "GENERAL_PURPOSE_SSD",
      "ebs_volume_count": 3,
      "ebs_volume_size": 100
    },
    "cluster_log_conf": {
      "s3": {
        "destination": "'"$LOG_DESTINATION_S3"'",
        "region": "us-east-1"
      }
    },
    "spark_conf": {
      "spark.ui.prometheus.enabled": true,
      "spark.dynamicAllocation.enabled": false,
      "spark.shuffle.service.enabled": true,
      "spark.streaming.dynamicAllocation.enabled": false,
      "spark.databricks.aggressiveWindowDownS": 600,
      "spark.databricks.aggressiveFirstStepScaleUpMax": 1,
      "spark.databricks.aggressiveFirstStepScaleUpFraction": 0.05,
      "spark.executor.processTreeMetrics.enabled": true
    },
    "custom_tags": {
      "Billing": "'"$CLUSTER_NAME"'"
    },
    "spark_env_vars": {
      "ENV_FOR_DYNACONF": "'"$ENV_FOR_DYNACONF"'",
      "CLUSTER_NAME": "'"$CLUSTER_NAME"'",
      "MAX_WORKERS": '"$MAX_WORKERS"'
    },
    "init_scripts": [
      {
        "s3": {
          "destination": "'"$INIT_SCRIPTS_DESTINATION_S3"'",
          "region": "us-east-1"
        }
      }
    ]
  },
  "spark_python_task": {
    "python_file": "file:/app/run.py"
  },
  "max_retries": -1,
  "max_concurrent_runs": 1
}'

echo job_settings: $job_settings

#################################################################################################################
# Function for creating new job if no job exists
#################################################################################################################
function create_job {
  echo "Creating job ..."

  new_job_response="$( \
  curl -X POST -H 'Content-Type: application/json' -H 'Authorization: Bearer '"$DATABRICKS_API_TOKEN"'' \
  $DATABRICKS_WORKSPACE/api/2.0/jobs/create -d ''"$job_settings"'' \
  '' \
  )"

  echo new_job_response: $new_job_response

  job_id="$(jq -n "$new_job_response" | jq --raw-output '.job_id')"

  echo job_id: $job_id

  # fail if creating new job fails
  [[ "$job_id" = null ]] && echo "Creating new job failed!" && exit 1
}

#################################################################################################################
# Function for resetting job if job exists
#################################################################################################################
function reset_job {
  echo "Resetting job ..."

  # reset job settings

  RESET_DATA='{
    "job_id": '"$job_id"',
    "new_settings": '"$job_settings"'
  }'

  echo $RESET_DATA

  reset_job_response="$( \
  curl -X POST -H 'Content-Type: application/json' -H 'Authorization: Bearer '"$DATABRICKS_API_TOKEN"'' \
  $DATABRICKS_WORKSPACE/api/2.0/jobs/reset -d ''"$RESET_DATA"'' \
  )"

  echo reset_job_response: $reset_job_response

  # fail if resetting old job fails
  [[ "$reset_job_response" != {} ]] && echo "Resetting old run failed! New run will not start!" && exit 1

  # get old run id for job

  list_run_response="$( \
  curl -X GET -H 'Content-Type: application/json' -H 'Authorization: Bearer '"$DATABRICKS_API_TOKEN"'' \
  $DATABRICKS_WORKSPACE/api/2.0/jobs/runs/list?job_id=''"$job_id"''&active_only=true \
  )"

  echo list_run_response: $list_run_response

  old_run_id="$(jq -n "$list_run_response" | jq --raw-output '.runs | .[] | select((.state.life_cycle_state == "RUNNING") or (.state.life_cycle_state == "PENDING")) | .run_id')"

  echo old_run_id: $old_run_id

  # cancel old run

  cancel_run_response="$( \
  curl -X POST -H 'Content-Type: application/json' -H 'Authorization: Bearer '"$DATABRICKS_API_TOKEN"'' \
  $DATABRICKS_WORKSPACE/api/2.0/jobs/runs/cancel -d '{"run_id": "'$old_run_id'"}' \
  )"

  echo cancel_run_response: $cancel_run_response

  # fail if canceling old job fails
  [[ "$cancel_run_response" != {} ]] && echo "Canceling old run failed! New run will not start!" && exit 1

  # wait for run to cancel
  sleep 10
}

#################################################################################################################
# 1. List existing jobs and find the job id with cluster name
#################################################################################################################
job_id="$( \
curl -X GET -H 'Content-Type: application/json' -H 'Authorization: Bearer '"$DATABRICKS_API_TOKEN"'' \
$DATABRICKS_WORKSPACE/api/2.0/jobs/list | \
jq --raw-output '.jobs | .[] | select(.settings.name == "'"$CLUSTER_NAME"'") | .job_id' \
)"

echo job_id: $job_id

#################################################################################################################
# 2. Decide next step based on number of jobs found
# - If job doesn't exist, then create job
# - If one job exists, then reset job
# - If more than one job exists, then fail (this should never happen)
#################################################################################################################

job_count="$(echo $job_id | wc -w)"

echo job_count $job_count

if [ $job_count = 0 ]; then
  echo "No existing job found. Creating new job ..."
  create_job
elif [ $job_count = 1 ]; then
  echo "Job found. Resetting job ..."
  reset_job
else
  echo "More than one job found. Failing deployment ..." && exit 1
fi

#################################################################################################################
# 3. Run new job
# the api returns {"run_id":123,"number_in_job":1}
#################################################################################################################

run_job_response="$( \
curl -X POST -H 'Content-Type: application/json' -H 'Authorization: Bearer '"$DATABRICKS_API_TOKEN"'' \
$DATABRICKS_WORKSPACE/api/2.0/jobs/run-now -d '{"job_id": "'"$job_id"'"}' \
)"

echo run_job_response: $run_job_response
