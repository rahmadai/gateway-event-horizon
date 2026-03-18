output "endpoint" {
  description = "RDS endpoint"
  value       = aws_db_instance.main.endpoint
}

output "replica_endpoint" {
  description = "RDS replica endpoint"
  value       = var.environment == "production" ? aws_db_instance.replica[0].endpoint : null
}

output "db_name" {
  description = "Database name"
  value       = aws_db_instance.main.db_name
}
