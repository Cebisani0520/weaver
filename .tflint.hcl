config {
  call_module_type = "local"
}

plugin "terraform" {
  enabled = true
  preset  = "recommended"
}

rule "terraform_documented_variables" {
  enabled = true
}

rule "terraform_documented_outputs" {
  enabled = true
}

rule "terraform_typed_variables" {
  enabled = true
}

rule "terraform_naming_convention" {
  enabled = true
}

# Stacks and roots split files by concern (floci.tf, kafka.tf, ...), so only
# modules are held to main/variables/outputs.
rule "terraform_standard_module_structure" {
  enabled = false
}
