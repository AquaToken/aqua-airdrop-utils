import argparse
import csv

from sys import exit

from stellar_sdk import Network, Server
from stellar_sdk.transaction_builder import TransactionEnvelope


if __name__ == "__main__":
    '''
    Example:
        python submitter.py
            --xdr_list_file=generated_signed_xdrs.csv
            --network=testnet
    '''

    parser = argparse.ArgumentParser(
        description='This script allows to distribute the asset airdrop '
                    'by submitting signed transactions to the network.'
    )

    parser.add_argument(
        '--xdr_list_file', nargs=1, help='Path to a CSV file with the list of accounts.', required=True,
    )
    parser.add_argument(
        '--network', nargs=1, help='Stellar network: ["testnet", "public"].', required=True,
    )

    try:
        args = parser.parse_args()
    except argparse.ArgumentError:
        print('Invalid arguments')
        exit(1)

    try:
        path_to_file = args.xdr_list_file[0]
    except Exception:
        print('Invalid --xdr_list_file')
        exit(1)

    network = args.network[0]
    if network not in ["testnet", "public"]:
        print('Invalid --network')
        exit(1)


    if network == 'testnet':
        server = Server(horizon_url="https://horizon-testnet.stellar.org")
        network_passphrase = Network.testnet_network().network_passphrase
    elif network == 'public':
        server = Server(horizon_url="https://horizon.stellar.org")
        network_passphrase = Network.public_network().network_passphrase


    with open(path_to_file) as csv_file:
        try:
            csv_reader = csv.reader(csv_file, delimiter=',')
        except Exception:
            print('Invalid {0} file'.format(path_to_file))
            exit(1)
        
        line_number = 0
        for row in csv_reader:
            xdr = row[0]

            te = TransactionEnvelope.from_xdr(xdr, network_passphrase)

            print("Line number {} is processing. Transaction hash: {}".format(line_number, te.hash_hex()))

            response = server.submit_transaction(xdr)
            line_number += 1

        print("Transactions successfully submitted to the network.")
