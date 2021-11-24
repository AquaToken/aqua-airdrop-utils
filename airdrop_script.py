import argparse
import csv
import time

from sys import exit
from dateutil.parser import parse
from decimal import Decimal, ROUND_DOWN
from typing import List, Sequence

from stellar_sdk import Asset, Claimant, ClaimPredicate, Keypair, Network, Server
from stellar_sdk.transaction_builder import TransactionBuilder, TransactionEnvelope


class SecuredWallet(object):
    def __init__(self, public_key, secret):
        self.public_key = public_key
        self.secret = secret


class AirdropGenerator(object):
    def __init__(
        self, asset, distribution_wallet, network,collector_public_key, claim_allowed_after, claim_allowed_before,
    ):
        self.asset = asset
        self.distribution_wallet = distribution_wallet
        self.collector = collector_public_key

        self.claim_allowed_after = claim_allowed_after
        self.claim_allowed_before = claim_allowed_before

        if network == 'testnet':
            self.server = Server(horizon_url="https://horizon-testnet.stellar.org")
            self.network_passphrase = Network.testnet_network().network_passphrase
        elif network == 'public':
            self.server = Server(horizon_url="https://horizon.stellar.org/")
            self.network_passphrase = Network.public_network().network_passphrase

    def _get_accounts_page(self, accounts):
        holders_head = slice(0, 100)

        page = accounts[holders_head]

        return page, holders_head

    def _get_builder(self, sequence_number=None):
        server_account = self.server.load_account(self.distribution_wallet.public_key)
        if sequence_number is None:
            sequence_number = server_account.sequence
        else:
            server_account.sequence = sequence_number

        base_fee = self.server.fetch_base_fee()

        memo = '{0} airdrop'.format(self.asset.code)

        builder = TransactionBuilder(
            source_account=server_account,
            network_passphrase=self.network_passphrase,
            base_fee=base_fee,
        ).add_text_memo(memo)
        return builder, sequence_number

    def _build_transaction(
        self, accounts: Sequence[str], base_amount: Decimal, sequence_number,
    ) -> TransactionEnvelope:
        builder, sequence_number = self._get_builder(sequence_number)

        for account in accounts:
            account_claimant = Claimant(
                destination=account[0],
                predicate=ClaimPredicate.predicate_and(
                    ClaimPredicate.predicate_not(
                        ClaimPredicate.predicate_before_absolute_time(self.claim_allowed_after)
                    ),
                    ClaimPredicate.predicate_before_absolute_time(self.claim_allowed_before)
                ),
            )
            collector_claimant = Claimant(
                destination=self.collector,
                predicate=ClaimPredicate.predicate_not(
                    ClaimPredicate.predicate_before_absolute_time(self.claim_allowed_before)
                ),
            )

            amount = Decimal(
                base_amount * account[1]
            ).quantize(
                Decimal('.0000001'),
                rounding=ROUND_DOWN,
            )
            builder.append_create_claimable_balance_op(
                claimants=[account_claimant, collector_claimant],
                asset=self.asset,
                amount=amount,
            )

        return builder.build(), sequence_number

    def _process_page(self, accounts_page: List, base_amount: Decimal, sequence_number):
        transaction_envelope, sequence_number= self._build_transaction(
            accounts_page, base_amount, sequence_number,
        )
        transaction_envelope.sign(self.distribution_wallet.secret)

        return transaction_envelope, sequence_number

    def _save_xdrs(self, xdr_list, **kwargs):
        if not xdr_list:
            return

        filename = kwargs.get('filename')

        with open(filename, mode='w') as payments:
            payments_writer = csv.writer(payments, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

            for row in xdr_list:
                payments_writer.writerow([row])


    def generate_payments(self, account_list: Sequence[str], base_amount: Decimal):
        page, accounts_slice = self._get_accounts_page(account_list)

        if not page:
            return

        xdr_list = []
        page_number = 1
        sequence_number = None

        try:
            while page:
                print("Started the processing of page number {}.".format(page_number))
                transaction_envelope, sequence_number = self._process_page(page, base_amount, sequence_number)

                sequence_number += 1

                xdr_list.append(transaction_envelope.to_xdr())

                del account_list[accounts_slice]

                page, accounts_slice = self._get_accounts_page(account_list)
                page_number += 1
        except KeyboardInterrupt:
            print("Processing aborted.")
        finally:
            self._save_xdrs(
                xdr_list, filename='generated_xdrs_{0}.csv'.format(int(time.time()))
            )


if __name__ == "__main__":
    '''
    Example:
        python airdrop_script.py
            --asset=XXX:GB5SFF6NUMW3C2RRCYTTVTLUICR5RSPIDHMTFXKCDK5TO3LOUL6IIGGG
            --distribution_wallet_public=GBKY7DHCVUFGJWVROGWG2XRYFKTKRUS245WPZLP7NLVC7PBRMSOSSIJN
            --distribution_wallet_secret=SXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
            --network=testnet --base_amount=1.01 --accounts_list_file=accounts.csv
            --collector_public_key=GD3NA637HY4GAVMRGMAZXVUIAIXTYSOHVKSPH3TUBKKJZHFQ55YZ54WD
            --start_date=2021-08-16T00:00:00Z
            --end_date=2021-09-16T00:00:00Z
    '''

    parser = argparse.ArgumentParser(
        description='This script allows to generate a CSV file with airdrop transactions based on input parameters.',
    )

    parser.add_argument(
        '--asset', nargs=1, help='A unique asset to be distributed. The expected format is CODE:ISSUER', required=True,
    )
    parser.add_argument(
        '--distribution_wallet_public', nargs=1, help='Distribution wallet public key', required=True,
    )
    parser.add_argument(
        '--distribution_wallet_secret', nargs=1, help='Distribution wallet signing key', required=True,
    )
    parser.add_argument(
        '--network', nargs=1, help='Stellar network: ["testnet", "public"].', required=True,
    )
    parser.add_argument(
        '--accounts_list_file', nargs=1, help='Path to a CSV file with the list of accounts', required=True,
    )
    parser.add_argument(
        '--base_amount', nargs=1, help='Base token amount a user will receive.', required=True,
    )
    parser.add_argument(
        '--collector_public_key', nargs=1, required=True,
        help='Public key of the wallet that will collect unclaimed balances.',
    )
    parser.add_argument(
        '--start_date', nargs=1, help='User can claim the balance starting from this date.', required=True,
    )
    parser.add_argument(
        '--end_date', nargs=1, help='Date from which an unclaimed balance can be collected back.', required=True,
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
        distribution_wallet_public = Keypair.from_public_key(args.distribution_wallet_public[0]).public_key
    except Exception:
        print('Invalid --distribution_wallet_public')
        exit(1)

    try:
        base_amount = Decimal(args.base_amount[0])
    except Exception:
        print('Invalid --base_amount')
        exit(1)

    try:
        distribution_wallet_secret = args.distribution_wallet_secret[0]
        Keypair.from_secret(args.distribution_wallet_secret[0])
    except Exception:
        print('Invalid --distribution_wallet_secret')
        exit(1)

    try:
        path_to_file = args.accounts_list_file[0]
    except Exception:
        print('Invalid --accounts_list_file')
        exit(1)
    
    try:
        collector_public_key = args.collector_public_key[0]
        Keypair.from_public_key(collector_public_key)
    except Exception:
        print('Invalid --collector_public_key')
        exit(1)

    try:
        start_date = args.start_date[0]
        start_date = int(parse(start_date).timestamp())
    except Exception:
        print('Invalid --start_date')
        exit(1)
    
    try:
        end_date = args.end_date[0]
        end_date = int(parse(end_date).timestamp())
    except Exception:
        print('Invalid --end_date')
        exit(1)
    
    distribution_wallet = SecuredWallet(distribution_wallet_public, distribution_wallet_secret)

    accounts_list = []

    with open(path_to_file) as csv_file:
        try:
            csv_reader = csv.reader(csv_file, delimiter=',')
        except Exception:
            print('Invalid {0} file'.format(path_to_file))
            exit(1)
        
        line_number = 0
        for row in csv_reader:
            print("Line {0} is processing".format(line_number))
            try:
                Keypair.from_public_key(row[0])
                if int(row[1]) != Decimal(row[1]):
                    raise Exception('Invalid multiplier')
            except Exception:
                print("Invalid account at line {0}: {1}".format(line_number, row[0]))
            else:
                accounts_list.append([row[0], int(row[1])])

            line_number += 1

        print("Wallet processing complete. The number of wallets is {0}".format(len(accounts_list)))

    payer = AirdropGenerator(
        asset=asset, distribution_wallet=distribution_wallet, network=network,
        collector_public_key=collector_public_key, claim_allowed_after=start_date,
        claim_allowed_before=end_date,
    )
    payer.generate_payments(accounts_list, base_amount)
