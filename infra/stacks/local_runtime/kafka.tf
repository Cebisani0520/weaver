# Single Confluent Platform broker in KRaft mode (no ZooKeeper).
#   - containers and pods on the network use broker:29092
#   - the laptop uses localhost:<ports.kafka>
module "broker" {
  source = "../../modules/docker_container"

  name         = "broker"
  image        = "confluentinc/cp-kafka:${var.confluent_platform_version}"
  network_name = module.network.name

  env = {
    CLUSTER_ID                                     = var.kafka_cluster_id
    KAFKA_NODE_ID                                  = "1"
    KAFKA_PROCESS_ROLES                            = "broker,controller"
    KAFKA_CONTROLLER_QUORUM_VOTERS                 = "1@broker:29093"
    KAFKA_LISTENERS                                = "PLAINTEXT://broker:29092,CONTROLLER://broker:29093,PLAINTEXT_HOST://0.0.0.0:9092"
    KAFKA_ADVERTISED_LISTENERS                     = "PLAINTEXT://broker:29092,PLAINTEXT_HOST://localhost:${var.ports.kafka}"
    KAFKA_LISTENER_SECURITY_PROTOCOL_MAP           = "CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT"
    KAFKA_CONTROLLER_LISTENER_NAMES                = "CONTROLLER"
    KAFKA_INTER_BROKER_LISTENER_NAME               = "PLAINTEXT"
    KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR         = "1"
    KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR = "1"
    KAFKA_TRANSACTION_STATE_LOG_MIN_ISR            = "1"
    KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS         = "0"
    KAFKA_AUTO_CREATE_TOPICS_ENABLE                = "false" # topics come from topics/*.yaml
    KAFKA_LOG_DIRS                                 = "/var/lib/kafka/data"
  }

  ports = [{ internal = 9092, external = var.ports.kafka }]

  volumes = [
    { container_path = "/var/lib/kafka/data", volume_name = "weaver-kafka-data" },
  ]

  healthcheck = {
    test = ["CMD", "kafka-broker-api-versions", "--bootstrap-server", "broker:29092"]
  }
}

module "broker_ready" {
  source = "../../modules/local_wait"

  name    = "Kafka broker"
  command = "[ \"$(docker inspect -f '{{.State.Health.Status}}' ${module.broker.name})\" = healthy ]"
  trigger = module.broker.id
}

module "schema_registry" {
  source = "../../modules/docker_container"

  name         = "schema-registry"
  image        = "confluentinc/cp-schema-registry:${var.confluent_platform_version}"
  network_name = module.network.name

  env = {
    SCHEMA_REGISTRY_HOST_NAME                    = "schema-registry"
    SCHEMA_REGISTRY_LISTENERS                    = "http://0.0.0.0:8081"
    SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS = "broker:29092"
  }

  ports = [{ internal = 8081, external = var.ports.schema_registry }]

  depends_on = [module.broker_ready]
}

module "schema_registry_ready" {
  source = "../../modules/local_wait"

  name    = "Schema Registry"
  command = "curl -fsS http://localhost:${var.ports.schema_registry}/subjects"
  trigger = module.schema_registry.id
}

# Lightweight open-source Kafka UI. Swap the image for Confluent Control Center
# if the team has a licence for it (see README, "UIs").
module "kafka_ui" {
  source = "../../modules/docker_container"
  count  = var.kafka_ui_enabled ? 1 : 0

  name         = "kafka-ui"
  image        = var.kafka_ui_image
  network_name = module.network.name

  env = {
    KAFKA_CLUSTERS_0_NAME             = "weaver-local"
    KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS = "broker:29092"
    KAFKA_CLUSTERS_0_SCHEMAREGISTRY   = "http://schema-registry:8081"
  }

  ports = [{ internal = 8080, external = var.ports.kafka_ui }]

  depends_on = [module.schema_registry_ready]
}
