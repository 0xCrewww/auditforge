# Example Run

## Input Contract

A simple vulnerable ERC-20 token contract for demonstration:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.7.0;

contract VulnerableToken {
    mapping(address => uint256) public balances;
    mapping(address => mapping(address => uint256)) public allowances;
    
    string public name = "Vulnerable Token";
    string public symbol = "VULN";
    uint8 public decimals = 18;
    uint256 public totalSupply = 1000000 * 10**18;
    
    address public owner;
    
    constructor() {
        owner = msg.sender;
        balances[msg.sender] = totalSupply;
    }
    
    // VULNERABLE: No reentrancy guard
    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        
        // VULNERABLE: External call before state update
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        
        // State update AFTER external call — reentrancy!
        balances[msg.sender] -= amount;
    }
    
    // VULNERABLE: Integer overflow in Solidity <0.8.0
    function transfer(address to, uint256 amount) public returns (bool) {
        balances[msg.sender] -= amount; // Can underflow
        balances[to] += amount; // Can overflow
        return true;
    }
    
    // VULNERABLE: tx.origin for authentication
    function changeOwner(address newOwner) public {
        require(tx.origin == owner, "Not owner");
        owner = newOwner;
    }
    
    // VULNERABLE: Unchecked return value
    function unsafeTransfer(address to, uint256 amount) public {
        // Return value of call is ignored
        to.call{value: amount}("");
    }
}
```

## API Request

```bash
curl -X POST http://localhost:8000/api/audit \
  -F "file=@VulnerableToken.sol"
```

## API Response

```json
{
  "audit_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "running",
  "filename": "VulnerableToken.sol",
  "estimated_lines": 45,
  "message": "Audit started. Poll GET /api/audit/{audit_id} for results."
}
```

## Polling

```bash
# Poll every 3 seconds
while true; do
  RESULT=$(curl -s http://localhost:8000/api/audit/a1b2c3d4-e5f6-7890-abcd-ef1234567890)
  STATUS=$(echo $RESULT | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  echo "Status: $STATUS"
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  sleep 3
done
```

## Expected Findings (from the 5 agents)

### Vulnerability Scanner would identify:
- **CRITICAL**: Reentrancy in `withdraw()` (SWC-107) — external call before state update
- **HIGH**: Integer overflow/underflow (SWC-101) — Solidity 0.7.x without SafeMath
- **HIGH**: tx.origin authentication (SWC-115) — susceptible to phishing attacks
- **MEDIUM**: Unchecked call return value (SWC-104) — `unsafeTransfer` ignores failure

### Logic Auditor would identify:
- **HIGH**: No access control on `transfer()` and `withdraw()`
- **MEDIUM**: No event emissions for transfers — hinders off-chain monitoring
- **LOW**: No pause/emergency mechanism

### Gas Analyst would identify:
- **MEDIUM**: Use `unchecked` blocks for arithmetic (if Solidity upgraded to 0.8+)
- **LOW**: Mark `name`, `symbol`, `decimals` as `immutable` or `constant`
- **LOW**: Use `calldata` instead of `memory` for string parameters

### Compliance Checker would identify:
- **HIGH**: Missing `Transfer` and `Approval` events (ERC-20 requirement)
- **HIGH**: `transfer()` does not return `bool` — violates ERC-20
- **MEDIUM**: Missing `approve()` return value

## Token Consumption (approximate)

- Total LLM calls: ~6 (4 agents + report + synthesis)
- Estimated total tokens: ~35,000–50,000
- Estimated time: ~45–90 seconds
