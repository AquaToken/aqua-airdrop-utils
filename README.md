# Aquarius initial airdrop scripts (Python)

## Overview 

This repository contains scripts that allow to hold an asset distribution (airdrop) using claimable balance transactions on the Stellar network.

## Usage

### Generator module

Generates a CSV file with airdrop transactions based on input parameters.

```
python airdrop_script.py
    --asset=XXX:GB5SFF6NUMW3C2RRCYTTVTLUICR5RSPIDHMTFXKCDK5TO3LOUL6IIGGG
    --distribution_wallet_public=GBKY7DHCVUFGJWVROGWG2XRYFKTKRUS245WPZLP7NLVC7PBRMSOSSIJN
    --distribution_wallet_secret=SXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    --network=testnet --base_amount=1.01 --accounts_list_file=accounts.csv
    --collector_public_key=GD3NA637HY4GAVMRGMAZXVUIAIXTYSOHVKSPH3TUBKKJZHFQ55YZ54WD
    --start_date=2021-08-16T00:00:00Z
    --end_date=2021-09-16T00:00:00Z
```


### Signer module

Signs airdrop transactions with a specified signing key and generates a CSV file with signed transactions.

```
python signer.py
    --xdr_list_file=generated_xdrs.csv
    --network=testnet
    --signer_key=SXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```



### Submitter module

Distributes the asset airdrop by submitting signed transactions to the network.

```
python submitter.py
    --xdr_list_file=generated_signed_xdrs.csv
    --network=testnet
```



### Collector module

Collects balances unclaimed by airdrop participants to a specified wallet address.

```
python collect.py
    --asset=XXX:GB5SFF6NUMW3C2RRCYTTVTLUICR5RSPIDHMTFXKCDK5TO3LOUL6IIGGG
    --collector_secret=SXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    --network=testnet
    --collector_public=GASTWQZSZFLID4DEIGX4KFKQRJKD55EZB72SKWOHIOB35KMFEHSTCYBA
```
