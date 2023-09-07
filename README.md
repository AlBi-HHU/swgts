# Installation

SWGTS comes packaged as an out-of-the box docker compose application. 

[References]



## Folder Structure

The software expects the following folders to exist:

input

output

By design we also require encrypted communication via TLS, this means that you need to have a valid certificate. You can create a self-signed certificate (for testing purposes) using:

```
openssl req -new -newkey rsa:2048 -sha256 -days 365 -nodes -x509 -keyout server.pem -out server.crt
```

The paths to server.pem and server.crt can be adjusted in docker-compose.yml.

### Apache Configuration



## Example Reference Construction 

You can use the fetchExampleDatabase.sh script to generate a combined database of human (T2T) and hCoV-19. This requires minimap2 to be installed (also takes a significant amount of memory).



# CLI Client

An example implementation of a CLI client is provided in the submodule [TODO]. To run it create a virtual environment for example using

```
mamba env create -f [TODO]/requirements.txt -n [TODO]
```

(Make sure that conda-forge is your default channel which should be the case in newer conda installations)

Then execute using:

```
python -m [TODO]
```


# Node.js Frontend

A website frontend is also included in the docker application and can be found in the folder [swgts-frontend]. Requests are forwarded to localhost by default (assuming the backend is located on the same machine), this can be adjusted in the package.json proxy directive.

# REST API

## GET /api/server-status
response: 200

response body: 

    {
    'commit' : String,
    'version' : String,
    'date' : String,
    'uptime' : Float,
    'maximum pending bytes' : Integer
    }

## POST /api/context/create
expected json : 

    {
    'filenames' : List[String] #List of all the files that are to be transmitted
    }

response: 200

## POST /api/context/<uuid:context_id>/reads
expected json : 

    'List[List[List[String]]]' #For each read index, for each file contains a list of the 4 lines making up one read

response: 200

response body: 

    {
    'processed reads' : Integer,
    'pending bytes' : Integer
    }
or

response: 400

response body: 

    {
    'message' : String
    }
or

response: 404

response body: 

    {
    'message' : String
    }

or

response: 422

response header: 

    {
    'Retry-After' : Float
    }
response body: 

    {
    'message' : String
    'processed reads' : Integer,
    'pending bytes' : Integer
    }

## POST /api/context/<uuid:context_id>/close

response: 200

response body: 

    {
    'processed reads' : Integer,
    'pending bytes' : Integer
    }
or

response: 503

response header: 

    {
    'Retry-After' : Float
    }
response body: 

    {
    'message' : String
    }
