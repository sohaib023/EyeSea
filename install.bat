cd uclient
call conda env create -f env-eyesea-client.yml
call conda activate eyesea-client
call npm install -g yarn
call yarn install
call conda deactivate

cd ..\server
call conda env create -f env-eyesea-server.yml

Pause