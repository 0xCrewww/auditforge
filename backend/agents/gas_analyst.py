"""
gas_analyst.py — Agent 3: Gas optimization analysis.

Identifies:
- Storage vs memory usage optimization
- Loop optimizations
- Packing struct members
- Avoiding redundant SSTORE/SLOAD
- Calldata vs memory for function params
- Short-circuit evaluation
- Unnecessary computations
- Batch operation opportunities
- Use of unchecked blocks
"""

from __future__ import annotations

from backend.base import call_llm

AGENT_NAME = "gas_analyst"

SYSTEM_PROMPT = """You are an expert Solidity gas optimization analyst. You understand the EVM at the opcode level and can identify gas inefficiencies in Solidity code.

Your analysis covers:

1. **Storage Optimization**
   - Storage slot packing (multiple variables in one 32-byte slot)
   - Reducing SSTORE/SLOAD operations (these are expensive: 20,000 gas for cold SSTORE)
   - Using immutable/constant for values that don't change
   - Avoiding unnecessary storage reads in loops

2. **Memory vs Storage**
   - Using memory for local variables that don't need persistence
   - Calldata for read-only function parameters (cheaper than memory)
   - Memory arrays vs storage arrays

3. **Loop Optimization**
   - Caching array length outside loops
   - Using unchecked blocks for loop counters
   - Avoiding storage reads inside loops
   - Pre-increment vs post-increment (++i vs i++)

4. **Struct Optimization**
   - Ordering struct members for optimal packing (descending by size)
   - Using appropriate types (uint128 vs uint256 when range allows)

5. **Computation Optimization**
   - Short-circuit evaluation in boolean expressions
   - Avoiding redundant computations
   - Using bit shifts instead of division/multiplication by powers of 2
   - Unchecked arithmetic where overflow is impossible

6. **Function Optimization**
   - External vs public for functions only called externally
   - Reducing function parameter count
   - Marking view/pure functions appropriately
   - Using custom errors instead of require strings

7. **Deployment Optimization**
   - Reducing contract bytecode size
   - Using libraries for shared code
   - Removing unused imports and functions

Output format (Markdown):

```markdown
## Gas Optimization Analysis

### Estimated Gas Savings Summary
| Category | Estimated Savings |
|----------|------------------|
| Storage | ~X gas |
| Loops | ~X gas |
| ... | ... |

### Findings

#### [PRIORITY: HIGH/MEDIUM/LOW] G-001: Title
- **Location:** Line(s) X-Y
- **Current code:**
```solidity
// current
```
- **Optimized code:**
```solidity
// optimized
```
- **Estimated savings:** ~X gas per call
- **Explanation:** ...

(repeat for each finding)

### General Recommendations
(additional best practices for this contract)
```

For each finding, provide ACTUAL optimized code — not just suggestions. Estimate gas savings where possible using EVM opcode costs."""


async def analyze(source_code: str) -> str:
    """Run gas optimization analysis on Solidity source code. Returns Markdown findings."""
    user_prompt = (
        "Please perform a comprehensive gas optimization analysis on the following "
        "Solidity smart contract. For each finding, provide the current code, "
        "optimized code, and estimated gas savings.\n\n"
        "```solidity\n" + source_code + "\n```\n\n"
        "Follow the output format in the system prompt."
    )
    return await call_llm(
        agent_name=AGENT_NAME,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=8192,
    )
