# Innotter Service

## Description

This project is a microservice for managing user content.

The service allows users to create personal pages, publish posts, like content, and follow other users. Authentication is handled through a separate User Management Service. 

## Features

- User pages management
- Post creation and management
- Like system
- User subscriptions (follow/unfollow)
- JWT-based permissions
- Token validation through the User Management Service
- REST API with Django REST Framework
- Background tasks with Celery, Celery-Beat
- Automated testing
- CI/CD with GitHub Actions

## Technology Stack

### Backend
- Django
- Django REST Framework
- MySQL Client
- Boto3
- JWT 
- Celery
- Logging
- Pytest

### Database
- MySQL

### CI/CD
- GitHub Actions

## Project Workflow

The project includes:

- Django project setup
- Docker and Docker Compose configuration
- Linter configuration
- Database and model implementation
- Django REST Framework setup
- API endpoints for pages, posts, likes, and followers
- JWT-based permissions
- Token validation through the User Management Service
- Background tasks with Celery
- Celery Beat scheduled jobs for page unblocking
- Unit and integration tests with Pytest
- Automated lint, test and build pipelines using GitHub Actions

## Authentication

This service does not store or issue JWT tokens.

Authentication and authorization are provided by a separate the User Management Service. User access tokens are validated through that service before protected operations are performed.

## CI/CD

GitHub Actions automatically runs:

- Linting
- Tests
- Build checks

for every push and pull request.

## Code Quality

The project uses:

- ruff, mypy

for code formatting and code quality checks.

## Testing
Tests are automatically executed by GitHub Actions on every push and pull request.
 
The CI pipeline includes:
- Automated test execution
- Code quality checks
- Build validation
