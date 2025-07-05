# Docker-based Antivirus API using ClamAV

This project provides a simple, containerized RESTful API for scanning files for viruses. It uses Python Flask as the API layer and ClamAV as the backend scanning engine. The entire application is managed by Docker Compose for easy setup and deployment.

### Project Structure

```
.
├── api/
│   ├── app.py             # The Flask API code
│   ├── Dockerfile         # Docker instructions for the API service
│   └── requirements.txt   # Python dependencies
└── docker-compose.yml     # Orchestrates the API and ClamAV services
```

### Prerequisites

* Docker
* Docker Compose

### Setup & Installation

1.  **Save the Files:** Create the directory structure and files as provided. Place `docker-compose.yml` in the root directory, and the other three files inside the `api/` subdirectory.

2.  **Build and Run the Services:** Open a terminal in the root directory of the project and run the following command:

    ```bash
    docker-compose up --build -d
    ```

    * `--build`: This flag tells Docker Compose to build the API image from the `Dockerfile`. You only need to use this the first time or when you make changes to the API code.
    * `-d`: This runs the containers in detached mode (in the background).

3.  **Initial Virus Database Download:** The first time you start the `clamav` container, it will download the entire virus signature database. This can take **5-10 minutes** and consume significant bandwidth. The API will not be fully functional until this process is complete.

    You can monitor the progress with the command:
    ```bash
    docker-compose logs -f clamav
    ```
    Look for messages indicating that the database is up to date. Press `Ctrl+C` to stop viewing the logs.

### How to Use the API

Once the services are running and the ClamAV database is updated, you can send files to the `/scan` endpoint for scanning.

#### Endpoint

`POST /scan`

#### Request

The request must be a `multipart/form-data` request with a single file field named `file`.

#### Example using `curl`

To scan a PDF file named `mydocument.pdf`, run the following command in your terminal:

```bash
curl -X POST \
  -F "file=@/path/to/your/mydocument.pdf" \
  http://localhost:5001/scan
```
*Replace `/path/to/your/mydocument.pdf` with the actual path to the file you want to scan.*