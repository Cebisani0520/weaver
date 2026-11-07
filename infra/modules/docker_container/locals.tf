locals {
  named_volumes = toset([
    for volume in var.volumes : volume.volume_name if volume.volume_name != null
  ])
}
