@echo off
cd ../uclient 
call conda activate eyesea-client
        
echo ******************************************
echo ******************************************
echo ******* LAUNCHING FRONT END SERVER *******
echo ******************************************
echo ******************************************

@echo on
yarn start