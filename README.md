# SWGTS

## Installation

SWGTS comes packaged as an out-of-the box docker compose application.

In order to start the software you need to:

- Generate the folder structure ([see below](#folder-structure))
- Provide a TLS certificate ([see below](#tls))
- Configure/Provide a database ([see below](#example-reference-construction))

### Folder Structure

The software expects the following folders to exist:

- input
- output

### TLS

By design we also require encrypted communication via TLS, this means that you need to have a valid certificate. You can create a self-signed certificate (for testing purposes) using:

```sh
openssl req -new -newkey rsa:2048 -sha256 -days 365 -nodes -x509 -keyout server.pem -out server.crt
```

The paths to server.pem and server.crt can be adjusted in docker-compose.yml.

### Example Reference Construction

You can use the fetchExampleDatabase.sh script to generate a combined database of human (T2T) and hCoV-19. This requires minimap2 to be installed (also takes a significant amount of memory).

## Basic Program Structure

The software consists of the following containers:

- Traefik, used as a reverse proxy to forward the incoming requests to the API/Frontend. Also serves as a load balancer
- Redis is used as a fast and efficient key,value storage and maintains the currently pending reads that need to be filtered.
- SWGTS-API handles the communication with clients
- SWGTS-Filter performs the actual host depletion with mappy

## CLI Client

An example implementation of a CLI client is provided in the subfolder [swgts-submit](swgts-submit). To run it create a virtual environment for example using

```sh
mamba env create -f swgts-submit/requirements.txt -n swgts-submit
```

(Make sure that conda-forge is your default channel which should be the case in newer conda installations)

Then execute using:

```sh
cd swgts-submit
python -m swgts-submit --server https://example.com/swgts/api example_data/example_cov_ont_reads.fq
```

to send an example file to a swgts server running on the domain `www.example.com`. The chunk size, i.e., the amount of bases sent to the server at one time, can be adjusted with the `--count` argument.
As a default setting this is a fraction of the server's buffer size to allow efficient parallelization.
Note that if the chunk size exceeds the buffer size the server will reject the transmission.

## Node.js Frontend

A website frontend is also included in the docker application and can be found in the folder [swgts-frontend](swgts-frontend). Requests are forwarded to localhost by default (assuming the backend is located on the same machine), this can be adjusted in the `package.json` proxy directive.

## Configuration Options

Configuration of the software is done via two configuration files that are generated on first launch in the input folder: `config_api.py` and `config_filter.py`.
In addition, you can edit the `docker-compose.yml` file to scale up individual components.
Since the entire system is stateless it is for example possible to use multiple API containers or even distribute them to different machines. For the filter component it is recommended
to utilize multiple threads (see below) instead of using multiple containers since this allows to take advantage of shared memory, drastically reducing the memory footprint in many scenarios.

### config_api.py

Configurable options are:

#### HANDS_OFF

If this is set to true the server will not save anything to disk. This can be useful if the server is just used to guarantee uniform host depletion quality or to take load off client machines. The clients are still able to reconstruct filtered read files based on the server responses.

#### MAXIMUM_PENDING_BYTES

This is the buffer size and limits how many bases can be held in RAM per context at any time. Decreasing this increases transmission times but reduces the risk of personal identification.

#### CONTEXT_TIMEOUT

If this timeout in seconds is exceeded a upload that was inactive will be removed.

### config_filter.py

Configurable options are:

#### FILTER_MODE

Can be set to POSITIVE (retention) or NEGATIVE (host subtraction).

#### MINIMAP2_POSITIVE_CONTIG

This is used for POSITIVE (retention) based modes and is used to identify the reference to which reads should align in order to be retained.

#### MAPPING_PRESET

Can be used to adjust for short reads (sr) or long reads (map-ont).

#### MINIMAP2_QUALITY_THRESHOLD

This is used for the NEGATIVE mode and requires an additional mapping quality to filter a read.

#### WORKER_THREADS

The amount of worker threads that are used in each filter container. The set of worker threads share the same database and thus require it to only be loaded into memory once.

## Example Interaction

Alice is a hosting provider and wants to collect reads of a target pathogen potentially contaminated with reads of human hosts.
Two collaborating parties, Bob and Christine, want to send their reads to Alice.
Since Alice wants to guarantee that the reads are depleted of host reads with sufficient quality, she hosts the SWGTS software under her domain
`www.example.com`. Bob has no experience with CLI-based tools and just opens the website `www.example.com/swgts/frontend` in his browser.
He drags the `.fastq` file containing the reads onto the screen and starts the upload process. Christine wants to upload data while it is being
sequenced and uses the CLI client to initiate an upload. She has previously followed the installation instructions listed above and created a conda environment
for the CLI client. Now, she invokes

```sh
python3 -m swgts-submit --server https://example.com/swgts/api christines_reads.fastq --outfolder local_out
```

while the file **christines_reads.fastq** is still being generated by her connected sequencing machine. Since she also wants to have a copy
of the host-depleted reads, she provides the outfolder argument which results in the CLI client writing a depleted .fastq to the given folder.

## REST API

In the following section we document the REST API. This can be of relevance if you are interested in implementing your own client.

### GET /api/server-status

HTTP response code: 200 (OK)
HTTP response body:

```json
{
  "commit": "String",
  "version": "String",
  "date": "String",
  "uptime": 23.14,
  "maximum pending bytes": 100000
}
```

### POST /api/context/create

HTTP request body:
List of all the files that are to be transmitted.

```json
{
  "filenames": [
    "pair1.fastq",
    "pair2.fastq"
  ]
}
```

HTTP response code: 200 (OK)

### POST /api/context/<uuid:context_id>/reads

HTTP request body:

```json
 # For each read index, for each file contains a list of the 4 lines making up one read
[
  [
    [
      "...",
      "...",
      "...",
      "...."
    ]
  ]
]
```

HTTP response code: 200 (OK)
HTTP response body:

```json
{
  "processed reads": 901000,
  "pending bytes": 9000
}
```

or

HTTP response code: 400 (Bad Request)
HTTP response body:

```json
{
  "message": "Error message"
}
```

or

HTTP response code: 404 (Not Found)
HTTP response body:

```json
{
  "message": "Error message"
}
```

or

HTTP response code: 422 (Unprocessable Content)
HTTP response header includes 'Retry-After'.
HTTP response body:

```json
{
  "message": "Error message",
  "processed reads": 47119000,
  "pending bytes": 18000
}

```

### POST /api/context/<uuid:context_id>/close

HTTP response code: 200 (OK)
HTTP response body:

```json
{
  "processed reads": 15000001,
  "pending bytes": 234568
}
```

or

HTTP response code: 503 (Service Unavailable)
HTTP response header includes 'Retry-After'.
HTTP response body:

```json
{
  "message": "Error message"
}
```

## Benchmarking

We provide a Jupyter Notebook with benchmarking scripts (designed for two machines) in the benchmarking folder.
A conda environment definition file is included that contains the required python packages.

## References

SWGTS uses minimap2's (<https://doi.org/10.1093/bioinformatics/bty191>) in-memory version mappy as the default mapping tool.
