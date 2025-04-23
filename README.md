# PulseScout

PulseScout is an AI-enhanced lead generation platform that helps businesses discover targeted email leads using advanced search tools.

## Project Structure

The project follows a microservice architecture with separate frontend and backend components:

- **Frontend**: React application with Tailwind CSS
- **Backend**: FastAPI Python application
- **Database**: PostgreSQL
- **Cache**: Redis
- **Message Broker**: RabbitMQ
- **Task Queue**: Celery

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Git

### Setup and Installation

1. Clone the repository
```bash
git clone [repository-url]
cd PulseScout
```

2. Create environment files
```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

3. Edit the environment files with your configuration

4. Start the development environment
```bash
docker-compose up -d
```

5. Access the application
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - RabbitMQ Management: http://localhost:15672 (guest/guest)

## Development

### Backend Development

The backend is built with FastAPI and follows a modular structure:

- `app/api/endpoints`: API route handlers
- `app/api/models`: Pydantic models for request/response validation
- `app/core`: Core functionality, configuration, and security
- `app/db`: Database models and queries
- `app/services`: Business logic services
- `app/ai`: AI/ML model integration
- `app/celery`: Background task processing

### Frontend Development

The frontend is built with React and follows a component-based architecture:

- `src/components`: Reusable UI components
- `src/pages`: Page-level components
- `src/redux`: Redux state management
- `src/api`: API client functions
- `src/hooks`: Custom React hooks
- `src/utils`: Utility functions

## AI Components

PulseScout leverages several AI tools:

- **spaCy (NER)**: Extracts entities from text data
- **Sentence-Transformers**: Semantic search capabilities
- **LightGBM**: Lead scoring and prioritization
- **Hunter.io API**: Email address generation

## Deployment

The application is designed to be deployed on AWS using:

- Frontend: S3 + CloudFront
- Backend: Elastic Beanstalk
- Database: RDS (PostgreSQL)
- Cache: ElastiCache (Redis)
- Message Queue: Amazon MQ (RabbitMQ)

CI/CD pipelines are set up using GitHub Actions to automate the deployment process.

## License

[License Information]