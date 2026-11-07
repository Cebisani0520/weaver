# Week 1: the root exists so the Floci S3 backend and provider are proven before
# any stack lands here. Stacks are added as they are built:
#
#   module "aws"             { source = "../../stacks/aws" }              # week 2+
#   module "ml"              { source = "../../stacks/ml" }               # week 3
#   module "confluent_local" { source = "../../stacks/confluent_local" }  # week 2
#   module "flink_local"     { source = "../../stacks/flink_local" }      # week 2, 4
