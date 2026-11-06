# EcoChain Shipping - Blockchain Shop & Tracker (Demo)

A simple, self-contained Python/Tkinter app that demonstrates how a
blockchain and a smart contract can sit behind an everyday online
shopping experience. It has two linked screens:

1. **Shop** - a small storefront (product grid, cart, checkout) where
   placing an order writes it to a blockchain and funds a smart contract
   for the payment.
2. **Blockchain Ledger** - push that order through its shipping lifecycle
   (picked up -> in transit -> delivered) and watch the smart contract
   auto-release payment the moment delivery is confirmed, with SHA-256
   used directly in the code to fingerprint and verify every record.

No external services, no real cryptocurrency, no installs beyond Python
itself - everything runs locally and in memory, which makes it easy to
read end to end and present as a working model.

---

## Features

- **Blockchain component** - every shipment event (order placed, picked
  up, in transit, delivered, etc.) is stored as a `Block`. Each block is
  fingerprinted with **SHA-256** (`hashlib.sha256`) over its data and the
  previous block's hash, so the blocks form a tamper-evident chain.
- **Smart contract (simulated escrow)** - placing an order locks in a
  price and creates a contract with status `Escrowed`. Confirming
  delivery automatically calls `contract.release()`, which flips it to
  `Released` and writes a "Payment Released" block - it will never
  release the same payment twice.
- **Tamper detection** - a "Verify Chain Integrity" button recomputes
  every block's hash and checks the hash-links between blocks. A
  "Simulate Tampering" button lets you edit a block's data without
  updating its hash, so you can immediately see verification catch it.
- **Shopping front end** - a product grid with "Add to Cart", a live
  cart with running total, and a checkout form that creates the order
  and jumps you straight to the ledger to see the new block.

---

## Requirements

- Python 3.8 or later
- Tkinter (ships with most Python installs)
  - If you get `ModuleNotFoundError: No module named 'tkinter'` on Linux:
    `sudo apt install python3-tk` (Debian/Ubuntu) or the equivalent for
    your distro.
  - Windows and macOS installers from python.org include Tkinter by
    default.

No `pip install` is required - the app only uses the standard library
(`hashlib`, `json`, `time`, `tkinter`).

---

## Running it

```bash
python3 ecochain_gui.py
```

A window opens on the **Shop** page.

---

## Walkthrough

1. **Shop page** - click "Add to Cart" on a few products. The cart
   sidebar updates with items, quantities and a running total.
2. Click **"Proceed to Checkout"**, enter a name and shipping address,
   then **"Place Order"**.
   - This creates a new order ID (`ORD-001`, `ORD-002`, ...), adds an
     "Order Placed" block to the chain, and funds a `SmartContract` for
     the order total (status `Escrowed`).
   - The app switches you to the **Blockchain Ledger** page so you can
     see the new block right away.
3. On the **Blockchain Ledger** page, the Order ID is pre-filled. Pick
   the next event from the dropdown (e.g. "Package Picked Up", "In
   Transit", "Out for Delivery") and click **"Add Block to Chain"** to
   log each step.
4. Choose **"Delivered - Proof Confirmed"** and add it:
   - The smart contract automatically releases the payment.
   - A new "Smart Contract: Payment Released" block is added to the
     chain, and the "Smart Contract" column updates from `Escrowed` to
     `Released`.
5. Click **"Verify Chain Integrity"** to confirm every hash and link is
   valid.
6. Click **"Simulate Tampering"** to silently alter the last block's
   location, then **"Verify Chain Integrity"** again - it reports the
   exact block where the hash no longer matches, demonstrating why
   SHA-256 hashing makes tampering detectable.
7. Click **"Reset Demo"** to clear the chain, cart and contracts and
   start over, or **"<- Back to Shop"** to keep shopping.

Click any row in the ledger table to see that block's full detail
(timestamp, data, stored hash, recomputed hash, previous hash) in the
panel below the table.

---

## Code structure

Everything lives in one file, `ecochain_gui.py`:

| Section | Purpose |
|---|---|
| `Block` | One shipment event; computes its own SHA-256 hash from its data + previous hash. |
| `Blockchain` | Holds the list of blocks; `add_block()` appends a new one, `is_valid()` checks the whole chain. |
| `SmartContract` | One per order; tracks `amount` and `status` (`Escrowed` -> `Released`); `release()` is idempotent. |
| `PRODUCTS` | The product catalog shown on the Shop page. |
| `EcoChainApp` | The Tkinter app: builds the Shop page and the Blockchain page as two stacked frames and switches between them. |

---

## Limitations (by design, to keep this a readable demo)

- This is a **simulation** for teaching/demo purposes, not a real
  blockchain or payment system - there is no networking, consensus,
  mining, or actual money movement.
- All state (chain, cart, contracts) lives in memory and resets when you
  restart the app or click "Reset Demo".
- One smart contract per order; it only ever moves `Escrowed -> Released`.
