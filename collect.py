import argparse
import csv
import time

from sys import exit

from billiard.exceptions import SoftTimeLimitExceeded
from decimal import Decimal
from typing import List, Sequence

from stellar_sdk import Asset, Claimant, Keypair, Network, Server
from stellar_sdk.exceptions import BaseHorizonError, NotFoundError
from stellar_sdk.transaction_builder import TransactionBuilder, TransactionEnvelope


class Collector(object):
    def __init__(self, asset, network, collector_public, collector_secret):
        self.asset = asset
        self.collector_public = Keypair.from_public_key(collector_public)
        self.collector_secret = Keypair.from_secret(collector_secret)

        server, network_passphrase = self.get_stellar_network_accessors(network)
        self.server = server
        self.network_passphrase = network_passphrase

    def get_stellar_network_accessors(self, network):
        if network == 'testnet':
            server = Server(horizon_url="https://horizon-testnet.stellar.org")
            network_passphrase = Network.testnet_network().network_passphrase
        elif network == 'public':
            server = Server(horizon_url="https://horizon.stellar.org")
            network_passphrase = Network.public_network().network_passphrase
        
        return server, network_passphrase

    def get_page(self):
        return self.server.claimable_balances().for_claimant(
            self.collector_public.public_key
        ).limit(100).call()['_embedded']['records']

    def _get_builder(self):
        server_account = self.server.load_account(self.collector_public.public_key)
        base_fee = self.server.fetch_base_fee()

        memo = '{0} claimback'.format(self.asset.code)

        builder = TransactionBuilder(
            source_account=server_account,
            network_passphrase=self.network_passphrase,
            base_fee=base_fee,
        ).add_text_memo(memo)
        return builder

    def _build_transaction(
        self, page: Sequence,
    ) -> TransactionEnvelope:
        builder = self._get_builder()

        for balance in page:
            builder.append_claim_claimable_balance_op(
                source=self.collector_public.public_key,
                balance_id=balance['id'],
            )

        return builder.build()

    def collect(self):
        server, network_passphrase = self.get_stellar_network_accessors(network)

        prev_page = None
        page = self.get_page()
        page_number = 1

        try:
            while page:
                transaction_envelope = self._build_transaction(page)
                transaction_envelope.sign(self.collector_secret.secret)

                try:
                    response = self.server.submit_transaction(transaction_envelope)
                    print("Processed page: {}".format(page_number))
                    page_number += 1
                except SoftTimeLimitExceeded as timeout_exc:
                    print("Timeout")
                except BaseHorizonError as submit_exc:
                    if hasattr(submit_exc, 'status') and submit_exc.status in [503, 504]:
                        print('Timeout')
                    else:
                        operation_fail_reasons = submit_exc.extras.get('result_codes', {}).get('operations', [])

                        if operation_fail_reasons:
                            print(
                                "One or several operations returned an error: {}".format(
                                    ', '.join(operation_fail_reasons)
                                )
                            )
                        else:
                            operation_fail_reasons = submit_exc.extras.get('result_codes', {}).get('transaction', 'unknown_reason')
                            print('Transaction returned an error: {}'.format(operation_fail_reasons))
                except Exception as unknown_exc:
                    print('Unexpected error')


                if page == prev_page:
                    print("Warning: Received consecutive pages with the same claimable balances")

                prev_page = page
                page = self.get_page()
        except KeyboardInterrupt:
            print("Interrupted")


if __name__ == "__main__":
    '''
    Example:
        python collect.py
            --asset=XXX:GB5SFF6NUMW3C2RRCYTTVTLUICR5RSPIDHMTFXKCDK5TO3LOUL6IIGGG
            --collector_secret=SXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
            --network=testnet
            --collector_public=GASTWQZSZFLID4DEIGX4KFKQRJKD55EZB72SKWOHIOB35KMFEHSTCYBA
    '''

    parser = argparse.ArgumentParser(
        description='This script allows to collect balances unclaimed by airdrop participants to a specified wallet address.',
    )

    parser.add_argument(
        '--asset', nargs=1, help='Unique asset to be distributed. The expected format is CODE:ISSUER', required=True,
    )
    parser.add_argument(
        '--network', nargs=1, help='Stellar network: ["testnet", "public"].', required=True,
    )
    parser.add_argument(
        '--collector_secret', nargs=1, help='Signing key of the wallet that will collect unclaimed balances.', required=True,
    )
    parser.add_argument(
        '--collector_public', nargs=1, help='Public key of the wallet that will collect unclaimed balances.', required=True,
    )

    try:
        args = parser.parse_args()
    except argparse.ArgumentError:
        print('Invalid arguments')
        exit(1)

    network = args.network[0]
    if network not in ["testnet", "public"]:
        print('Invalid network')
        exit(1)

    try:
        asset = args.asset[0].split(":")
        asset = Asset(code=asset[0], issuer=asset[1])
    except (ValueError, IndexError):
        print('Invalid --asset')
        exit(1)

    try:
        collector_secret = Keypair.from_secret(args.collector_secret[0]).secret
    except Exception:
        print('Invalid --collector_secret')
        exit(1)

    try:
        collector_public = Keypair.from_public_key(args.collector_public[0]).public_key
    except Exception:
        print('Invalid --collector_public')
        exit(1)


    collector = Collector(
        asset=asset, collector_public=collector_public,
        network=network, collector_secret=collector_secret,
    )
    collector.collect()
