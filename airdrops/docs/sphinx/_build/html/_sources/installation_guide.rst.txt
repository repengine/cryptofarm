Installation Guide
==================

This guide provides step-by-step instructions for installing and setting up the Airdrops Automation system.

Prerequisites
-------------

Before installing the Airdrops Automation system, ensure you have the following prerequisites:

Python Version
~~~~~~~~~~~~~~

* **Python 3.11.0 or higher** (but less than 4.0)
* Verify your Python version: ``python --version``

Poetry Package Manager
~~~~~~~~~~~~~~~~~~~~~~

* **Poetry** for dependency management
* Install Poetry: https://python-poetry.org/docs/#installation
* Verify installation: ``poetry --version``

System Dependencies
~~~~~~~~~~~~~~~~~~~

The system may require additional build tools for certain Python packages with C extensions:

**Windows:**
  * Microsoft Visual C++ Build Tools
  * Windows SDK

**macOS:**
  * Xcode Command Line Tools: ``xcode-select --install``

**Linux (Ubuntu/Debian):**
  * Build essentials: ``sudo apt-get install build-essential``
  * Python development headers: ``sudo apt-get install python3-dev``

Git
~~~

* **Git** for cloning the repository
* Verify installation: ``git --version``

Installation Steps
------------------

1. Clone the Repository
~~~~~~~~~~~~~~~~~~~~~~~

Clone the Airdrops Automation repository to your local machine:

.. code-block:: bash

   git clone <repository-url>
   cd airdrops

2. Install Dependencies
~~~~~~~~~~~~~~~~~~~~~~~

Use Poetry to install all project dependencies:

.. code-block:: bash

   # Install all dependencies (including development dependencies)
   poetry install

   # Install only production dependencies
   poetry install --only=main

3. Activate Virtual Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Activate the Poetry-managed virtual environment:

.. code-block:: bash

   poetry shell

Alternatively, you can run commands within the virtual environment using:

.. code-block:: bash

   poetry run <command>

Environment Configuration
-------------------------

The Airdrops Automation system requires several environment variables to be configured for proper operation.

Environment Variables Setup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a ``.env`` file in the project root directory to store your environment variables:

.. code-block:: bash

   cp .env.example .env

Required Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Blockchain RPC URLs:**

.. code-block:: bash

   # Ethereum Mainnet
   ETHEREUM_RPC_URL=https://your-ethereum-rpc-url
   
   # Layer 2 Networks
   SCROLL_L1_RPC_URL=https://your-ethereum-rpc-url
   SCROLL_L2_RPC_URL=https://scroll-mainnet.rpc.url
   ZKSYNC_L1_RPC_URL=https://your-ethereum-rpc-url
   ZKSYNC_L2_RPC_URL=https://mainnet.era.zksync.io
   
   # Other Networks
   ARBITRUM_RPC_URL=https://arb1.arbitrum.io/rpc
   HYPERLIQUID_RPC_URL=https://api.hyperliquid.xyz

**Wallet Configuration:**

.. code-block:: bash

   # Private keys (use secure key management in production)
   WALLET_PRIVATE_KEY=0x...
   
   # Alternative: Wallet mnemonic
   WALLET_MNEMONIC="your twelve word mnemonic phrase here"
   
   # Wallet addresses for verification
   WALLET_ADDRESS=0x...

**API Keys (if required):**

.. code-block:: bash

   # External service API keys
   ALCHEMY_API_KEY=your_alchemy_key
   INFURA_API_KEY=your_infura_key
   MORALIS_API_KEY=your_moralis_key

**Database Configuration:**

.. code-block:: bash

   # SQLite (default for development)
   DATABASE_URL=sqlite:///./airdrops.db
   
   # PostgreSQL (recommended for production)
   DATABASE_URL=postgresql://user:password@localhost:5432/airdrops

**Monitoring Configuration:**

.. code-block:: bash

   # Prometheus metrics
   PROMETHEUS_PORT=8000
   
   # Alerting
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
   EMAIL_SMTP_SERVER=smtp.gmail.com
   EMAIL_SMTP_PORT=587
   EMAIL_USERNAME=your-email@gmail.com
   EMAIL_PASSWORD=your-app-password

Environment File Template
~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a ``.env.example`` file as a template:

.. code-block:: bash

   # Blockchain RPC URLs
   ETHEREUM_RPC_URL=https://your-ethereum-rpc-url
   SCROLL_L1_RPC_URL=https://your-ethereum-rpc-url
   SCROLL_L2_RPC_URL=https://scroll-mainnet.rpc.url
   ZKSYNC_L1_RPC_URL=https://your-ethereum-rpc-url
   ZKSYNC_L2_RPC_URL=https://mainnet.era.zksync.io
   ARBITRUM_RPC_URL=https://arb1.arbitrum.io/rpc
   HYPERLIQUID_RPC_URL=https://api.hyperliquid.xyz
   
   # Wallet Configuration
   WALLET_PRIVATE_KEY=0x...
   WALLET_ADDRESS=0x...
   
   # API Keys
   ALCHEMY_API_KEY=your_alchemy_key
   INFURA_API_KEY=your_infura_key
   
   # Database
   DATABASE_URL=sqlite:///./airdrops.db
   
   # Monitoring
   PROMETHEUS_PORT=8000
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
   EMAIL_SMTP_SERVER=smtp.gmail.com
   EMAIL_SMTP_PORT=587
   EMAIL_USERNAME=your-email@gmail.com
   EMAIL_PASSWORD=your-app-password

Initial Setup and Verification
-------------------------------

1. Verify Installation
~~~~~~~~~~~~~~~~~~~~~~

Run the following commands to verify your installation:

.. code-block:: bash

   # Check Python path and imports
   poetry run python -c "import airdrops; print('Installation successful!')"
   
   # Run basic tests
   poetry run pytest tests/ -v
   
   # Check code style
   poetry run flake8 src/
   
   # Type checking
   poetry run mypy src/

2. Database Initialization
~~~~~~~~~~~~~~~~~~~~~~~~~~

Initialize the database for analytics and monitoring:

.. code-block:: bash

   # Initialize database schema
   poetry run python -c "
   from airdrops.analytics.tracker import AirdropTracker
   tracker = AirdropTracker()
   print('Database initialized successfully!')
   "

3. Configuration Validation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Validate your configuration:

.. code-block:: bash

   # Test RPC connections
   poetry run python -c "
   from airdrops.shared.config import *
   from web3 import Web3
   
   # Test Ethereum connection
   w3 = Web3(Web3.HTTPProvider(SCROLL_L1_RPC_URL))
   print(f'Ethereum connected: {w3.is_connected()}')
   print(f'Latest block: {w3.eth.block_number}')
   "

4. Health Check
~~~~~~~~~~~~~~~

Run a comprehensive health check:

.. code-block:: bash

   # Run system health check
   poetry run python -c "
   from airdrops.monitoring.health_checker import HealthChecker
   
   health_checker = HealthChecker()
   status = health_checker.check_system_health()
   print(f'System health: {status}')
   "

Security Considerations
-----------------------

**Private Key Management:**

* Never commit private keys to version control
* Use environment variables or secure key management systems
* Consider using hardware wallets for production deployments
* Regularly rotate private keys

**RPC Endpoint Security:**

* Use authenticated RPC endpoints when possible
* Implement rate limiting and retry logic
* Monitor RPC usage and costs
* Use multiple RPC providers for redundancy

**Environment Security:**

* Restrict access to ``.env`` files
* Use proper file permissions (600)
* Consider using encrypted environment variable storage
* Audit environment variable access

Troubleshooting
---------------

Common Installation Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Poetry Installation Fails:**

.. code-block:: bash

   # Clear Poetry cache
   poetry cache clear --all pypi
   
   # Reinstall dependencies
   poetry install --no-cache

**Python Version Conflicts:**

.. code-block:: bash

   # Use specific Python version with Poetry
   poetry env use python3.11
   
   # Verify Python version in virtual environment
   poetry run python --version

**Build Tool Errors:**

* Ensure all system dependencies are installed
* Update build tools to latest versions
* Check compiler compatibility

**RPC Connection Issues:**

* Verify RPC URLs are correct and accessible
* Check network connectivity
* Validate API keys and authentication
* Test with alternative RPC providers

Getting Help
~~~~~~~~~~~~

If you encounter issues during installation:

1. Check the troubleshooting section above
2. Review the system logs for error details
3. Consult the project documentation
4. Open an issue on the project repository

Next Steps
----------

After successful installation, proceed to the :doc:`setup_guide` for detailed configuration of individual system components.