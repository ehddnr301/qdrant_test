#!/bin/bash

docker run -d   -p 6333:6333   -v $(pwd)/qdrant_storage:/qdrant/storage   --name qdrant   qdrant/qdrant