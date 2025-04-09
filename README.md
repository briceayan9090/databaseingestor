# XLSX Ingestor Application

This repository contains a containerized web application with a **PostGreSQL Database**
backend and a **Streamlit** frontend. The setup uses Docker Compose to simplify
deployment and local development, with live reloading enabled for seamless
updates.

---

## Getting Started

### Start the Application

Run the following command to build and start the containers:  

```docker-compose up```

This will: 

1. Build the Docker images for the PostGreSQL and Streamlit services.  
2. Start the containers and serve the application.  

---

## Features

- **PostGreSQL Database Backend**:  
  Hosted on <http://localhost:5432>  

- **Streamlit Frontend**:  
  Hosted on <http://localhost:8084>
  
---

## Prerequisites

Before you start, ensure the following tools are installed on your system:

- Docker  
- Docker Compose  

---

## Access the Application

- **PostGreSQL Database Backend**:  
  Visit <http://localhost:5432> to access the API.  

- **Streamlit Frontend**:  
  Visit <http://localhost:8084> to interact with the frontend.  

---

## Development Workflow

### Stopping the Application

To stop the application, press `Ctrl+C` or run the following command:  

docker-compose down  

This will stop and remove the containers, but the built images will remain.  

---

## Directory Structure

The project structure is as follows:  

.  
├── backend/               # PostGreSQL backend application  
│   ├── init.sql           # PostGreSQL file  
├── frontend/              # Streamlit application  
│   ├── app.py             # Streamlit entrypoint  
│   └── Dockerfile         # Dockerfile for Streamlit
│   └── requirements.txt   # Python dependencies for streamlit  
├── docker-compose.yml     # Docker Compose configuration  
└── README.md              # Project documentation  
```

---

## Troubleshooting

- Ensure Docker and Docker Compose are installed and running on your system.  
- Verify that the required ports (5432 and 8084) are not in use by other 
applications.  

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.
