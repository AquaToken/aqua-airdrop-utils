import argparse
import csv

from sys import exit

from stellar_sdk import Keypair, Network
from stellar_sdk.transaction_builder import TransactionEnvelope


if __name__ == "__main__":
    '''
    Example:
        python signer.py
            --xdr_list_file=generated_xdrs.csv
            --network=testnet
            --signer_key=SXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    '''

    parser = argparse.ArgumentParser(
        description='This script allows to sign airdrop transactions with a specified '
                    'signing key and generate a CSV file with signed transactions.',
    )

    parser.add_argument(
        '--xdr_list_file', nargs=1, help='Path to a CSV file with the list of accounts.', required=True,
    )
    parser.add_argument(
        '--network', nargs=1, help='Stellar network: ["testnet", "public"].', required=True,
    )
    parser.add_argument(
        '--signer_key', nargs=1, help='Additional signing key of the distribution wallet.', required=True,
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

    try:
        signer_key = args.signer_key[0]
        signer_key = Keypair.from_secret(signer_key)
    except Exception:
        print('Invalid --signer_key')
        exit(1)

    network = args.network[0]
    if network not in ["testnet", "public"]:
        print('Invalid --network')
        exit(1)


    if network == 'testnet':
        network_passphrase = Network.testnet_network().network_passphrase
    elif network == 'public':
        network_passphrase = Network.public_network().network_passphrase


    result = []
    line_number = 0
    with open(path_to_file) as csv_file:
        try:
            csv_reader = csv.reader(csv_file, delimiter=',')
        except Exception:
            print('Invalid {0} file'.format(path_to_file))
            exit(1)
        
        for row in csv_reader:
            print ("Processing line {}".format(line_number))
            xdr = row[0]

            te = TransactionEnvelope.from_xdr(xdr, network_passphrase)
            te.sign(signer_key)

            result.append(te.to_xdr())

            line_number += 1

    output_filename = path_to_file.split('.')
    output_filename[-2] += '_signed'
    output_filename = '.'.join(output_filename)
    with open(output_filename, mode='w') as output_file:
        xdr_writer = csv.writer(output_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        for row in result:
            xdr_writer.writerow([row])
