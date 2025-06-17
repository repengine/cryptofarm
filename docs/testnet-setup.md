# Testnet Setup Guide

This guide explains how to set up testnet wallets for running the cryptofarm mock validation tests.

## Prerequisites

- Python 3.8+
- Funded mainnet wallet (0.001 ETH minimum for most faucets)
- Twitter/Discord account for some faucets

## Generate Testnet Wallets

1. Run the wallet generation script:
```bash
cd airdrops/scripts
python generate_testnet_wallets.py
```

This will:
- Generate unique wallets for each testnet
- Save wallet details to `airdrops/testnet_wallets/wallets.json`
- Create `.env.testnet` file with private keys

2. **IMPORTANT**: The generated files contain private keys. Never commit them to version control!

## Fund Your Wallets

After generating wallets, you need to fund them with testnet tokens. Here are the recommended faucets:

### Ethereum Sepolia
- **Chainlink Faucet**: https://faucets.chain.link/sepolia
  - Requires: 1 LINK on mainnet
  - Gives: 0.5 ETH + 25 LINK
- **Alchemy Faucet**: https://www.alchemy.com/faucets/ethereum-sepolia
  - Requires: Free Alchemy account
  - Gives: 0.5 ETH per day
- **PoW Faucet**: https://sepolia-faucet.pk910.de/
  - Requires: Mining computation
  - Gives: Variable amount

### zkSync Era Sepolia
- **Chainlink Faucet**: https://faucets.chain.link/zksync-sepolia
- **Alchemy Faucet**: https://www.alchemy.com/faucets/zksync-sepolia
  - Requires: 0.001 ETH on zkSync mainnet
- **QuickNode**: https://faucet.quicknode.com/zksync/sepolia

### Scroll Sepolia
- **Chainlink Faucet**: https://faucets.chain.link/scroll-sepolia-testnet
- **Bware Labs**: https://bwarelabs.com/faucets/scroll-testnet
- **L2 Faucet**: https://www.l2faucet.com/scroll

### Arbitrum Sepolia
- **Chainlink Faucet**: https://faucets.chain.link/arbitrum-sepolia
- **Alchemy Faucet**: https://www.alchemy.com/faucets/arbitrum-sepolia
  - Requires: 0.01 ETH on Arbitrum mainnet

### Ethereum Holesky
- **Chainlink Faucet**: https://faucets.chain.link/holesky
- **Alchemy Faucet**: https://www.alchemy.com/faucets/ethereum-holesky
  - Requires: 0.001 ETH on mainnet
- **Google Cloud**: https://cloud.google.com/application/web3/faucet/ethereum/holesky

## Faucet Tips

1. **Anti-Bot Measures**: Most faucets require:
   - Mainnet balance (usually 0.001 ETH)
   - Social media verification
   - CAPTCHA completion

2. **Rate Limits**: 
   - Most faucets: Once per 24-72 hours
   - Some allow multiple drips with social sharing

3. **Best Practices**:
   - Use different wallets for different purposes
   - Keep track of which faucets you've used
   - Join Discord servers for additional faucet access

## Running Tests

Once wallets are funded, set the environment variables:

```bash
# Load testnet environment
source .env.testnet

# Or export individually
export TESTNET_PRIVATE_KEY_SEPOLIA="0x..."
export TESTNET_PRIVATE_KEY_ZKSYNC_SEPOLIA="0x..."
# etc...
```

Then run the mock validation tests:

```bash
cd airdrops
pytest tests/test_mock_validation.py -v
```

## Security Notes

- **Never use these wallets on mainnet**
- **Never share private keys**
- **Use dedicated wallets for testing only**
- **Regenerate wallets periodically**

## Troubleshooting

### Faucet Not Working
- Check mainnet balance requirements
- Try different faucets
- Wait for rate limit to reset
- Use VPN if region-blocked

### Transaction Failures
- Ensure sufficient gas
- Check network status
- Verify correct network selection

### Import Issues
- Some wallets need manual network addition
- Use correct RPC endpoints
- Verify chain IDs match