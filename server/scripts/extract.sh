#!/bin/bash
# One-shot: extract dbc, maps, vmaps and mmaps from the client mounted at /client into /data.
set -e

TOOLS=/opt/cmangos/bin/tools
cd "$TOOLS"
./ExtractResources.sh a /client /data
ls -la /data
