# Project Commandments for CryptoFarm

## Core Commandments

1. **The Prime Directive**: Before any task, ensure it directly contributes to at least one of:
   - **Delta-neutral**: Hedging mechanisms, position balancing, or risk reduction
   - **Automatic**: Reduces manual intervention, adds scheduling, or improves autonomous operation
   - **Sybil-proof**: Wallet isolation, activity randomization, or detection avoidance
   - **Farming efficiency**: Increases yield, reduces costs, or improves capital allocation
   
   If unclear, ask: "How does this make the system more automated, profitable, or undetectable?"

2. **Security First**: Never expose private keys, API keys, or sensitive data. Always use environment variables for secrets.

3. **Risk Management**: Every protocol integration must include proper risk assessment and capital allocation constraints.

4. **Automation**: Prefer automated solutions over manual interventions. The system should run autonomously.

5. **Sybil Resistance**: Design all systems with sybil attack prevention in mind.

6. **Testing**: Always write comprehensive tests for new features, especially for protocol integrations.

7. **Capital Efficiency**: Optimize for maximum airdrop returns while minimizing capital requirements and gas costs.

8. **Monitoring**: Ensure all critical operations have proper logging and monitoring.

9. **Documentation**: Keep code well-documented, but only create separate documentation files when explicitly requested.

10. **Fail-Safe**: Build with graceful degradation - if one protocol fails, others should continue operating.

## Project Goals
- Build a fully automated airdrop farming system
- Maintain delta-neutral positions to minimize market risk
- Support multiple protocols simultaneously
- Optimize capital allocation across opportunities
- Prevent detection as a farming operation

## Key Principles
- **Modularity**: Each protocol should be independently pluggable
- **Scalability**: Design for managing hundreds of wallets
- **Efficiency**: Minimize gas costs and maximize capital utilization
- **Resilience**: Handle failures gracefully without human intervention