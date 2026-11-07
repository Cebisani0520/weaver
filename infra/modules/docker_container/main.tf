resource "docker_image" "this" {
  name         = var.image
  keep_locally = true
}

resource "docker_volume" "this" {
  for_each = local.named_volumes

  name = each.value

  labels {
    label = "project"
    value = var.project
  }
}

resource "docker_container" "this" {
  name     = var.name
  hostname = var.name
  image    = docker_image.this.image_id
  restart  = var.restart
  must_run = true
  user     = var.user
  command  = var.command
  env      = [for key, value in var.env : "${key}=${value}"]

  networks_advanced {
    name    = var.network_name
    aliases = var.aliases
  }

  dynamic "ports" {
    for_each = var.ports
    content {
      internal = ports.value.internal
      external = ports.value.external
      ip       = var.bind_ip
    }
  }

  dynamic "volumes" {
    for_each = var.volumes
    content {
      container_path = volumes.value.container_path
      host_path      = volumes.value.host_path
      volume_name    = volumes.value.volume_name == null ? null : docker_volume.this[volumes.value.volume_name].name
      read_only      = volumes.value.read_only
    }
  }

  dynamic "healthcheck" {
    for_each = var.healthcheck == null ? [] : [var.healthcheck]
    content {
      test         = healthcheck.value.test
      interval     = healthcheck.value.interval
      timeout      = healthcheck.value.timeout
      retries      = healthcheck.value.retries
      start_period = healthcheck.value.start_period
    }
  }

  labels {
    label = "project"
    value = var.project
  }
}
