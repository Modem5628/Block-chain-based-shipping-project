"""
EcoChain Shipping - Blockchain Shipment Tracker (Demo)

A simple, self-contained Tkinter app with two pages:

  1. "Shop" - an online-storefront front end (product grid + cart +
     checkout) where placing an order creates a blockchain record and
     funds a smart contract for that order's payment.
  2. "Blockchain" - the ledger view, where you can push a shipment through
     its lifecycle (picked up -> in transit -> delivered) and watch the
     smart contract auto-release payment on delivery, with SHA-256 used
     directly in the code to fingerprint and verify every block.

A button in each page's header switches to the other page.

No external dependencies - uses only the Python standard library
(hashlib, json, time, tkinter).

Run:
    python3 ecochain_gui.py
"""

import hashlib
import json
import time
import tkinter as tk
from tkinter import ttk, messagebox


# ---------------------------------------------------------------------------
# Blockchain core (this is the "blockchain component")
# ---------------------------------------------------------------------------

class Block:
    """One block = one shipment event (order created, handoff, delivered...)."""

    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.data = data                  # dict describing the shipment event
        self.previous_hash = previous_hash
        self.hash = self.compute_hash()

    def compute_hash(self):
        """SHA-256 fingerprint of this block's contents.

        This is where SHA-256 is used directly in the code: we serialize the
        block's fields to a fixed, sorted JSON string and hash it. Changing
        even one character of the data produces a completely different hash.
        """
        block_string = json.dumps(
            {
                "index": self.index,
                "timestamp": self.timestamp,
                "data": self.data,
                "previous_hash": self.previous_hash,
            },
            sort_keys=True,
        )
        return hashlib.sha256(block_string.encode("utf-8")).hexdigest()


class Blockchain:
    """A simple append-only chain of shipment events."""

    def __init__(self):
        self.chain = [self._create_genesis_block()]

    def _create_genesis_block(self):
        return Block(
            index=0,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            data={"event": "Genesis Block", "info": "EcoChain ledger start"},
            previous_hash="0" * 64,
        )

    @property
    def last_block(self):
        return self.chain[-1]

    def add_block(self, data):
        new_block = Block(
            index=len(self.chain),
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            data=data,
            previous_hash=self.last_block.hash,
        )
        self.chain.append(new_block)
        return new_block

    def is_valid(self):
        """Checks every block's hash and hash-link to the previous block.

        Returns (True, None) if the chain is intact, or (False, index) for
        the first block where tampering is detected.
        """
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # Recompute the hash from the current data - if someone edited
            # the data without redoing this, the hashes won't match.
            if current.hash != current.compute_hash():
                return False, i
            # Check that this block still correctly points at the previous one.
            if current.previous_hash != previous.hash:
                return False, i
        return True, None


# ---------------------------------------------------------------------------
# Smart contract (very small simulated escrow, one per order)
# ---------------------------------------------------------------------------

class SmartContract:
    """Locks in a price when the order is placed, and releases it only once
    delivery is confirmed - mirroring the 'smart contract releases payment
    after delivery is confirmed' idea from the EcoChain concept.
    """

    def __init__(self, order_id, amount):
        self.order_id = order_id
        self.amount = amount
        self.status = "Escrowed"  # Escrowed -> Released

    def release(self):
        """Release payment once. Returns False if already released (so we
        never pay out twice for the same order)."""
        if self.status == "Released":
            return False
        self.status = "Released"
        return True


# ---------------------------------------------------------------------------
# Product catalog for the storefront page
# ---------------------------------------------------------------------------

PRODUCTS = [
    {"id": "P1", "name": "Reusable Eco Tote Bag", "price": 12.99, "icon": "🛍️",
     "desc": "Durable, washable, replaces hundreds of plastic bags."},
    {"id": "P2", "name": "Bamboo Cutlery Set", "price": 8.49, "icon": "🍴",
     "desc": "Travel-friendly set with a cotton carry pouch."},
    {"id": "P3", "name": "Solar Power Bank", "price": 34.99, "icon": "🔋",
     "desc": "10,000mAh, recharges via sunlight or USB-C."},
    {"id": "P4", "name": "Organic Cotton T-Shirt", "price": 19.99, "icon": "👕",
     "desc": "Certified organic cotton, unisex fit."},
    {"id": "P5", "name": "Recycled Paper Notebook", "price": 6.99, "icon": "📓",
     "desc": "100% post-consumer recycled pages."},
    {"id": "P6", "name": "Steel Water Bottle", "price": 15.49, "icon": "🚰",
     "desc": "Insulated, keeps drinks cold for 24 hours."},
]


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

class EcoChainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EcoChain - Shop & Blockchain Tracker")
        self.root.geometry("1080x660")
        self.root.minsize(980, 600)

        self.blockchain = Blockchain()
        self.known_orders = []
        self.contracts = {}      # order_id -> SmartContract
        self.cart = {}           # product_id -> {"product": dict, "qty": int}
        self.order_counter = 0

        self._build_style()

        # Two full-size pages stacked in the same spot; a button on each
        # switches to the other one.
        self.container = ttk.Frame(self.root)
        self.container.pack(fill="both", expand=True)
        self.container.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1)

        self.shop_page = ttk.Frame(self.container)
        self.chain_page = ttk.Frame(self.container)
        for page in (self.shop_page, self.chain_page):
            page.grid(row=0, column=0, sticky="nsew")

        self._build_shop_page(self.shop_page)
        self._build_chain_page(self.chain_page)

        self._refresh_cart_view()
        self._refresh_chain_view()
        self.show_shop()

    # -- page switching ----------------------------------------------------
    def show_shop(self):
        self.shop_page.tkraise()

    def show_chain(self):
        self._refresh_chain_view()
        self.chain_page.tkraise()

    # -- styling --------------------------------------------------------
    def _build_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", rowheight=26, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        style.configure("TButton", padding=6)
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Sub.TLabel", font=("Segoe UI", 9), foreground="#555555")
        style.configure("Price.TLabel", font=("Segoe UI", 11, "bold"), foreground="#1a7a1a")
        style.configure("Nav.TButton", padding=8)

    # =====================================================================
    # PAGE 1: SHOP (online-storefront front end)
    # =====================================================================
    def _build_shop_page(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=0)
        parent.rowconfigure(1, weight=1)

        header = ttk.Frame(parent, padding=(16, 12))
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.columnconfigure(0, weight=1)

        title_box = ttk.Frame(header)
        title_box.grid(row=0, column=0, sticky="w")
        ttk.Label(title_box, text="🌿 EcoChain Marketplace", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            title_box,
            text="Shop sustainably - every order is tracked, hashed and paid for on-chain",
            style="Sub.TLabel",
        ).pack(anchor="w")

        ttk.Button(
            header, text="View Blockchain Ledger  ⛓ ->", style="Nav.TButton", command=self.show_chain
        ).grid(row=0, column=1, sticky="e")

        # -- product grid -----------------------------------------------
        products_panel = ttk.Frame(parent, padding=(16, 0, 8, 16))
        products_panel.grid(row=1, column=0, sticky="nsew")
        for col in range(3):
            products_panel.columnconfigure(col, weight=1)

        for idx, product in enumerate(PRODUCTS):
            r, c = divmod(idx, 3)
            self._build_product_card(products_panel, product, r, c)

        # -- cart sidebar --------------------------------------------------
        cart_panel = ttk.LabelFrame(parent, text="🛒 Your Cart", padding=12)
        cart_panel.grid(row=1, column=1, sticky="nsew", padx=(0, 16), pady=(0, 16))
        cart_panel.rowconfigure(0, weight=1)
        cart_panel.columnconfigure(0, weight=1)
        cart_panel.columnconfigure(1, weight=1)

        columns = ("item", "qty", "subtotal")
        self.cart_tree = ttk.Treeview(cart_panel, columns=columns, show="headings", height=10)
        self.cart_tree.heading("item", text="Item")
        self.cart_tree.heading("qty", text="Qty")
        self.cart_tree.heading("subtotal", text="Subtotal")
        self.cart_tree.column("item", width=140, anchor="w")
        self.cart_tree.column("qty", width=35, anchor="center")
        self.cart_tree.column("subtotal", width=70, anchor="e")
        self.cart_tree.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 8))

        ttk.Button(cart_panel, text="- Remove", command=self.remove_from_cart).grid(
            row=1, column=0, sticky="ew", padx=(0, 3), pady=(0, 4)
        )
        ttk.Button(cart_panel, text="Clear Cart", command=self.clear_cart).grid(
            row=1, column=1, sticky="ew", padx=(3, 0), pady=(0, 4)
        )

        self.cart_total_var = tk.StringVar(value="Total: $0.00")
        ttk.Label(cart_panel, textvariable=self.cart_total_var, font=("Segoe UI", 12, "bold")).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(8, 10)
        )

        ttk.Button(cart_panel, text="Proceed to Checkout", command=self.open_checkout).grid(
            row=3, column=0, columnspan=2, sticky="ew"
        )

    def _build_product_card(self, parent, product, row, col):
        card = ttk.LabelFrame(parent, padding=10)
        card.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
        ttk.Label(card, text=f"{product['icon']}  {product['name']}",
                  font=("Segoe UI", 10, "bold"), wraplength=190).pack(anchor="w")
        ttk.Label(card, text=product["desc"], wraplength=190, style="Sub.TLabel").pack(
            anchor="w", pady=(4, 8)
        )
        ttk.Label(card, text=f"${product['price']:.2f}", style="Price.TLabel").pack(anchor="w")
        ttk.Button(card, text="Add to Cart", command=lambda p=product: self.add_to_cart(p)).pack(
            fill="x", pady=(8, 0)
        )

    # -- cart logic ----------------------------------------------------
    def add_to_cart(self, product):
        entry = self.cart.setdefault(product["id"], {"product": product, "qty": 0})
        entry["qty"] += 1
        self._refresh_cart_view()

    def remove_from_cart(self):
        selected = self.cart_tree.selection()
        if not selected:
            messagebox.showinfo("Nothing selected", "Select an item in the cart first.")
            return
        product_id = selected[0]
        if product_id in self.cart:
            del self.cart[product_id]
        self._refresh_cart_view()

    def clear_cart(self):
        self.cart = {}
        self._refresh_cart_view()

    def _refresh_cart_view(self):
        for row in self.cart_tree.get_children():
            self.cart_tree.delete(row)
        total = 0.0
        for product_id, entry in self.cart.items():
            product, qty = entry["product"], entry["qty"]
            subtotal = product["price"] * qty
            total += subtotal
            self.cart_tree.insert(
                "", "end", iid=product_id,
                values=(product["name"], qty, f"${subtotal:,.2f}"),
            )
        self.cart_total_var.set(f"Total: ${total:,.2f}")

    # -- checkout --------------------------------------------------------
    def open_checkout(self):
        if not self.cart:
            messagebox.showinfo("Cart is empty", "Add at least one item before checking out.")
            return

        modal = tk.Toplevel(self.root)
        modal.title("Checkout")
        modal.geometry("360x260")
        modal.transient(self.root)
        modal.grab_set()

        frame = ttk.Frame(modal, padding=16)
        frame.pack(fill="both", expand=True)

        total = sum(e["product"]["price"] * e["qty"] for e in self.cart.values())
        ttk.Label(frame, text="Confirm Your Order", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(frame, text=f"Order total: ${total:,.2f}", style="Price.TLabel").pack(
            anchor="w", pady=(2, 14)
        )

        ttk.Label(frame, text="Your Name").pack(anchor="w")
        name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=name_var).pack(fill="x", pady=(0, 10))

        ttk.Label(frame, text="Shipping Address").pack(anchor="w")
        address_var = tk.StringVar()
        ttk.Entry(frame, textvariable=address_var).pack(fill="x", pady=(0, 16))

        def confirm():
            buyer = name_var.get().strip()
            address = address_var.get().strip()
            if not buyer or not address:
                messagebox.showwarning("Missing info", "Please enter your name and shipping address.",
                                        parent=modal)
                return
            self._place_shop_order(buyer, address, total)
            modal.destroy()

        ttk.Button(frame, text="Place Order (funds smart contract)", command=confirm).pack(fill="x")

    def _place_shop_order(self, buyer, address, total):
        self.order_counter += 1
        order_id = f"ORD-{self.order_counter:03d}"

        items_summary = ", ".join(
            f"{e['qty']}x {e['product']['name']}" for e in self.cart.values()
        )

        # Fund a smart contract for this order's total - it stays "Escrowed"
        # until a "Delivered - Proof Confirmed" event is logged for it on
        # the Blockchain page.
        contract = SmartContract(order_id, total)
        self.contracts[order_id] = contract

        data = {
            "order_id": order_id,
            "event": "Order Placed",
            "sender": "EcoChain Marketplace",
            "receiver": buyer,
            "location": address,
            "items": items_summary,
            "amount": contract.amount,
            "payment_status": contract.status,
        }
        self.blockchain.add_block(data)

        self.known_orders.append(order_id)
        self.order_combo["values"] = self.known_orders
        self.order_id_var.set(order_id)
        self.receiver_var.set(buyer)
        self.location_var.set(address)

        self.clear_cart()
        messagebox.showinfo(
            "Order Placed",
            f"Order {order_id} placed for ${total:,.2f}.\n"
            "Payment is now held in escrow by the smart contract until delivery "
            "is confirmed on the Blockchain page.",
        )
        self.show_chain()

    # =====================================================================
    # PAGE 2: BLOCKCHAIN LEDGER
    # =====================================================================
    def _build_chain_page(self, parent):
        parent.columnconfigure(0, weight=0)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(1, weight=1)

        header = ttk.Frame(parent, padding=(16, 12))
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.columnconfigure(0, weight=1)

        title_box = ttk.Frame(header)
        title_box.grid(row=0, column=0, sticky="w")
        ttk.Label(title_box, text="⛓ EcoChain Blockchain Ledger", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            title_box,
            text="Every shipment event is a SHA-256-hashed block; delivery auto-releases payment",
            style="Sub.TLabel",
        ).pack(anchor="w")

        ttk.Button(
            header, text="<- Back to Shop  🛒", style="Nav.TButton", command=self.show_shop
        ).grid(row=0, column=1, sticky="e")

        main = ttk.Frame(parent, padding=(16, 0, 16, 16))
        main.grid(row=1, column=0, columnspan=2, sticky="nsew")
        main.columnconfigure(0, weight=0)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        self._build_control_panel(main)
        self._build_chain_panel(main)

    def _build_control_panel(self, parent):
        panel = ttk.LabelFrame(parent, text="New Shipment Event", padding=12)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        ttk.Label(panel, text="Order ID").grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.order_id_var = tk.StringVar()
        self.order_combo = ttk.Combobox(panel, textvariable=self.order_id_var, width=24)
        self.order_combo.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(panel, text="Sender").grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.sender_var = tk.StringVar()
        ttk.Entry(panel, textvariable=self.sender_var, width=27).grid(row=3, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(panel, text="Receiver").grid(row=4, column=0, sticky="w", pady=(0, 2))
        self.receiver_var = tk.StringVar()
        ttk.Entry(panel, textvariable=self.receiver_var, width=27).grid(row=5, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(panel, text="Event").grid(row=6, column=0, sticky="w", pady=(0, 2))
        self.event_var = tk.StringVar(value="Order Placed")
        event_combo = ttk.Combobox(
            panel,
            textvariable=self.event_var,
            state="readonly",
            width=24,
            values=[
                "Order Placed",
                "Package Picked Up",
                "In Transit",
                "Handed to Next Courier",
                "Out for Delivery",
                "Delivered - Proof Confirmed",
            ],
        )
        event_combo.grid(row=7, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(panel, text="Location").grid(row=8, column=0, sticky="w", pady=(0, 2))
        self.location_var = tk.StringVar()
        ttk.Entry(panel, textvariable=self.location_var, width=27).grid(row=9, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(panel, text="Price ($) - set when placing order").grid(
            row=10, column=0, sticky="w", pady=(0, 2)
        )
        self.price_var = tk.StringVar()
        ttk.Entry(panel, textvariable=self.price_var, width=27).grid(row=11, column=0, sticky="ew", pady=(0, 14))

        ttk.Button(panel, text="Add Block to Chain", command=self.add_shipment_event).grid(
            row=12, column=0, sticky="ew", pady=(0, 6)
        )
        ttk.Button(panel, text="Verify Chain Integrity", command=self.verify_chain).grid(
            row=13, column=0, sticky="ew", pady=(0, 6)
        )
        ttk.Button(panel, text="Simulate Tampering", command=self.simulate_tamper).grid(
            row=14, column=0, sticky="ew", pady=(0, 6)
        )
        ttk.Button(panel, text="Reset Demo", command=self.reset_chain).grid(row=15, column=0, sticky="ew")

        self.status_var = tk.StringVar(value="Chain OK - 1 block (genesis)")
        self.status_label = ttk.Label(
            panel, textvariable=self.status_var, foreground="#1a7a1a",
            wraplength=220, font=("Segoe UI", 9, "bold"),
        )
        self.status_label.grid(row=16, column=0, sticky="w", pady=(14, 0))

    def _build_chain_panel(self, parent):
        panel = ttk.LabelFrame(parent, text="Blockchain Ledger (each row = one block)", padding=12)
        panel.grid(row=0, column=1, sticky="nsew")
        panel.rowconfigure(0, weight=1)
        panel.columnconfigure(0, weight=1)

        columns = ("index", "event", "order", "location", "payment", "hash", "prev_hash")
        self.tree = ttk.Treeview(panel, columns=columns, show="headings", height=14)
        headings = {
            "index": "#",
            "event": "Event",
            "order": "Order / Parties",
            "location": "Location",
            "payment": "Smart Contract",
            "hash": "Block Hash (SHA-256)",
            "prev_hash": "Prev Hash",
        }
        widths = {
            "index": 35, "event": 150, "order": 160, "location": 100,
            "payment": 130, "hash": 150, "prev_hash": 150,
        }
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(panel, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<<TreeviewSelect>>", self._show_block_detail)

        detail = ttk.LabelFrame(parent, text="Block Detail", padding=10)
        detail.grid(row=1, column=1, sticky="nsew", pady=(12, 0))
        self.detail_text = tk.Text(detail, height=8, wrap="word", font=("Consolas", 9))
        self.detail_text.pack(fill="both", expand=True)
        self.detail_text.configure(state="disabled")

    # -- actions ----------------------------------------------------------
    def add_shipment_event(self):
        order_id = self.order_id_var.get().strip()
        sender = self.sender_var.get().strip()
        receiver = self.receiver_var.get().strip()
        location = self.location_var.get().strip() or "Unknown"
        event = self.event_var.get()

        if not order_id:
            messagebox.showwarning("Missing info", "Please enter an Order ID.")
            return

        # --- Smart contract: create it when the order is placed ---
        if event == "Order Placed" and order_id not in self.contracts:
            try:
                amount = float(self.price_var.get().strip() or 0)
            except ValueError:
                messagebox.showwarning("Invalid price", "Please enter the price as a number, e.g. 49.99")
                return
            self.contracts[order_id] = SmartContract(order_id, amount)

        contract = self.contracts.get(order_id)

        data = {
            "order_id": order_id,
            "event": event,
            "sender": sender or "-",
            "receiver": receiver or "-",
            "location": location,
        }
        if contract:
            data["amount"] = contract.amount
            data["payment_status"] = contract.status
        self.blockchain.add_block(data)

        if order_id not in self.known_orders:
            self.known_orders.append(order_id)
            self.order_combo["values"] = self.known_orders

        # --- Smart contract: auto-release payment once delivery is confirmed ---
        if event == "Delivered - Proof Confirmed" and contract and contract.release():
            release_data = {
                "order_id": order_id,
                "event": "Smart Contract: Payment Released",
                "sender": sender or "-",
                "receiver": receiver or "-",
                "location": location,
                "amount": contract.amount,
                "payment_status": contract.status,
            }
            self.blockchain.add_block(release_data)
            messagebox.showinfo(
                "Smart Contract Executed",
                f"Delivery confirmed for order {order_id}.\n"
                f"Smart contract automatically released ${contract.amount:,.2f} to the courier/seller.",
            )
        elif event == "Delivered - Proof Confirmed" and not contract:
            messagebox.showinfo(
                "No contract found",
                f"Order {order_id} was delivered, but it has no smart contract "
                "(no price was set when it was placed), so there is nothing to release.",
            )

        self._refresh_chain_view()
        self._set_status(True)

    def verify_chain(self):
        valid, bad_index = self.blockchain.is_valid()
        self._set_status(valid, bad_index)
        if valid:
            messagebox.showinfo(
                "Chain Verified",
                "All blocks are intact.\nEvery hash matches its data, and every "
                "block correctly links to the previous one.",
            )
        else:
            messagebox.showerror(
                "Tampering Detected",
                f"Problem found at block #{bad_index}.\n"
                "Its stored hash no longer matches its data, or its link to the "
                "previous block is broken - this is exactly how SHA-256 lets us "
                "detect tampering.",
            )
        self._refresh_chain_view()

    def simulate_tamper(self):
        if len(self.blockchain.chain) < 2:
            messagebox.showinfo("Nothing to tamper", "Add at least one shipment event first.")
            return
        # Secretly edit a block's data without recomputing its hash,
        # the way an attacker trying to alter a record would.
        target = self.blockchain.chain[-1]
        target.data["location"] = target.data.get("location", "") + " (ALTERED)"
        messagebox.showwarning(
            "Tampering Simulated",
            "The last block's location was silently edited, without updating "
            "its stored hash.\n\nClick 'Verify Chain Integrity' to see SHA-256 catch it.",
        )
        self._refresh_chain_view()

    def reset_chain(self):
        if messagebox.askyesno("Reset", "Clear the demo chain and start over?"):
            self.blockchain = Blockchain()
            self.known_orders = []
            self.contracts = {}
            self.order_combo["values"] = []
            self._refresh_chain_view()
            self._set_status(True)

    # -- view helpers -------------------------------------------------------
    def _refresh_chain_view(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for block in self.blockchain.chain:
            order = block.data.get("order_id", "-")
            sender = block.data.get("sender", "")
            receiver = block.data.get("receiver", "")
            order_cell = order if block.index == 0 else f"{order} ({sender} -> {receiver})"
            if "payment_status" in block.data:
                payment_cell = f"{block.data['payment_status']} (${block.data.get('amount', 0):,.2f})"
            else:
                payment_cell = "-"
            self.tree.insert(
                "", "end", iid=str(block.index),
                values=(
                    block.index,
                    block.data.get("event", block.data.get("info", "")),
                    order_cell,
                    block.data.get("location", "-"),
                    payment_cell,
                    block.hash[:16] + "...",
                    block.previous_hash[:16] + "...",
                ),
            )

    def _show_block_detail(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        index = int(selected[0])
        block = self.blockchain.chain[index]
        current_hash = block.compute_hash()
        tampered = current_hash != block.hash

        text = (
            f"Block #{block.index}\n"
            f"Timestamp:      {block.timestamp}\n"
            f"Data:           {json.dumps(block.data, indent=2)}\n"
            f"Stored Hash:    {block.hash}\n"
            f"Recomputed:     {current_hash}\n"
            f"Previous Hash:  {block.previous_hash}\n"
            f"Integrity:      {'TAMPERED - hash mismatch!' if tampered else 'OK'}\n"
        )
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", text)
        self.detail_text.configure(state="disabled")

    def _set_status(self, valid, bad_index=None):
        n = len(self.blockchain.chain)
        if valid:
            self.status_var.set(f"Chain OK - {n} block(s)")
            self.status_label.configure(foreground="#1a7a1a")
        else:
            self.status_var.set(f"Tamper detected at block #{bad_index}")
            self.status_label.configure(foreground="#b00020")


def main():
    root = tk.Tk()
    EcoChainApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
