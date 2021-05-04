#!/usr/bin/env bash

### Borrowed from: https://gist.github.com/Lowess/3a71792d2d09e38bf8f524644bbf8349#file-bootstrap-prometheus-sh
### The spark worker and executor nodes run the init-script.sh after launching the container
### https://docs.databricks.com/clusters/custom-containers.html#use-an-init-script

### Function that enables exporting of spark metrics to Prometheus

function setup_databricks_prometheus() {

  echo "Showing files in /databricks/spark/conf/*"
  ls -al /databricks/spark/conf/
  cat /databricks/spark/conf/spark.properties

  echo "Showing content of /databricks/spark/conf/metrics.properties"
  sudo touch /databricks/spark/conf/metrics.properties
  cat <<EOF | sudo tee /databricks/spark/conf/metrics.properties
# Enable Ganglia metrics
driver.sink.ganglia.class=org.apache.spark.metrics.sink.GangliaSink
*.sink.ganglia.port=8649
*.sink.ganglia.mode=unicast

# Enable Prometheus metrics
*.sink.prometheusServlet.class=org.apache.spark.metrics.sink.PrometheusServlet
*.sink.prometheusServlet.path=/metrics/prometheus
master.sink.prometheusServlet.path=/metrics/master/prometheus
applications.sink.prometheusServlet.path=/metrics/applications/prometheus
EOF

  sudo touch /databricks/spark/dbconf/log4j/master-worker/metrics.properties
  cat <<EOF | sudo tee /databricks/spark/dbconf/log4j/master-worker/metrics.properties
# Enable Prometheus metrics
*.sink.prometheusServlet.class=org.apache.spark.metrics.sink.PrometheusServlet
*.sink.prometheusServlet.path=/metrics/prometheus
master.sink.prometheusServlet.path=/metrics/master/prometheus
applications.sink.prometheusServlet.path=/metrics/applications/prometheus
EOF

  echo "Showing content of /databricks/spark/dbconf/log4j/master-worker/metrics.properties"
  cat /databricks/spark/dbconf/log4j/master-worker/metrics.properties

  echo "Showing SPARK_ related envvars"
  env | grep "SPARK_"

  echo "Local spark ip is: ${SPARK_LOCAL_IP:-'NONE'}"
}

### Main
setup_databricks_prometheus
