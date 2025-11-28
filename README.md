# Netskope CCI Tag Migrator

A Python utility to automate the migration of Cloud Confidence Index (CCI) tags and their associated applications from one Netskope tenant to another.

This script ensures a safe migration process by separating the extraction, mapping, application, and rollback phases into distinct steps.

## 🚀 Features

* **Step-by-step Execution**: Separate steps for fetching, mapping, and applying tags to ensure data integrity.
* **Selective Migration**: Choose to migrate all tags at once or a specific tag individually.
* **Idempotency**: Can be run multiple times; checks for existing data.
* **Rollback Capability**: Includes a safety mechanism to remove tags from the destination tenant based on the migration plan.
* **Detailed Logging**: Generates a `migration_log.log` file with full request/response details for troubleshooting.

## 📋 Prerequisites

### 1. Python Environment
* Python 3.6+
* `requests` library

```bash
pip install requests
