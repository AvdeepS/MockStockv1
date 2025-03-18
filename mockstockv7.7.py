
import streamlit as st
import pandas as pd
from st_supabase_connection import SupabaseConnection
# Custom CSS to hide elements and make the app full-screen
st.markdown(
    """
    <style>
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}

    /* Full-screen mode */
    .stApp {
        padding: 0 !important;
        margin: 0 !important;
        max-width: 100% !important;
        width: 100vw !important;
        height: 100vh !important;
    }

    /* Disable scrolling */
    body {
        overflow: hidden;
    }

    /* Custom styling for the main content */
    .main-content {
        padding: 10px;
        background-color: #f9f9f9;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    </style>
    """,
    unsafe_allow_html=True
)
conn = st.connection("supabase", type=SupabaseConnection)

# ---- Session State for Authentication ----

def initialize_session():
        if "user" not in st.session_state:
            st.session_state.user = None
            st.session_state.user_id = None  # Store User ID
        if 'cash' not in st.session_state:
            st.session_state.cash = 10000000000  # Starting cash
        if 'portfolio' not in st.session_state:
            st.session_state.portfolio = {}  # Stocks and derivatives holdings
        if 'transactions' not in st.session_state:
            st.session_state.transactions = []  # All transactions
        if 'round' not in st.session_state:
            st.session_state.round = 1  # Current round starts at 1
        if 'forex' not in st.session_state:
            st.session_state.forex = {}  # Forex holdings
        if 'derivatives' not in st.session_state:
            st.session_state.derivatives = {}  # Derivatives holdings
        if 'short_positions' not in st.session_state:  # Short positions
            st.session_state.short_positions = {}
        if 'companies' not in st.session_state:  # Initialize companies in session state
            st.session_state.companies = {f'Round {i}': {} for i in range(1, 8)}
        if 'forex_data' not in st.session_state:
            st.session_state.forex_data = {f'Round {i}': {} for i in range(1, 8)}
        if 'derivatives_data' not in st.session_state:
            st.session_state.derivatives_data = {f'Round {i}': {} for i in range(1, 8)}
        if 'section_31_fees_paid' not in st.session_state:
            st.session_state.section_31_fees_paid = 0  # Track Section 31 fees
        if 'green_bonds' not in st.session_state:
            st.session_state.green_bonds = {}  # Green bond investments
        if 'green_bond_interest' not in st.session_state:
            st.session_state.green_bond_interest = 0  # Interest earned from green bonds
        if 'loan_taken' not in st.session_state:
            st.session_state.loan_taken = 0  # Loans taken to meet the 15% rule
        if 'insider_purchases' not in st.session_state:
            st.session_state.insider_purchases = {}  # Insider hints purchased
        if 'loan' not in st.session_state:  # Loan details
            st.session_state.loan = {'amount': 0, 'interest_rate': 0.15, 'round_taken': None}
        
        current_round = st.session_state.get("current_round", 1)
        round_key = f"Round {current_round}"
        response = conn.client.from_("security_prices").select("*").execute()
        
        if response.data:
            for row in response.data:
                security_type = row['type']
                country = row['country']
                ticker = row['ticker']
                
                for i in range(1, 8):
                    round_key = f'Round {i}'
                    price = row[f'r{i}_price']
                    
                    if price is not None:
                        if security_type == 'stock':
                            if country not in st.session_state.companies[round_key]:
                                st.session_state.companies[round_key][country] = {}
                            st.session_state.companies[round_key][country][ticker] = price
                        elif security_type == 'forex':
                            if 'forex_data' not in st.session_state:
                                st.session_state.forex_data = {round_key: {} for round_key in st.session_state.companies}
                            st.session_state.forex_data[round_key][ticker] = {
                                'currency': ticker,
                                'exchange_rate': price
                            }
                        elif security_type == 'future':
                            if 'derivatives_data' not in st.session_state:
                                st.session_state.derivatives_data = {round_key: {} for round_key in st.session_state.companies}
                                
                            if security_type.capitalize() not in st.session_state.derivatives_data[round_key]:
                                st.session_state.derivatives_data[round_key][security_type.capitalize()] = {}

                            st.session_state.derivatives_data[round_key][security_type.capitalize()][ticker] = {
                                'contract_size': 10000,  # Assuming a default contract size
                                'price': price
                            }
                
                # Handle the 'final' price
                if row['final'] is not None:
                    if security_type == 'stock':
                        if 'Final' not in st.session_state.companies:
                            st.session_state.companies['Final'] = {}
                        if country not in st.session_state.companies['Final']:
                            st.session_state.companies['Final'][country] = {}
                        st.session_state.companies['Final'][country][ticker] = row['final']
        else:
            st.error("Failed to fetch security prices from Supabase.")
def invest_in_green_bond(bond_name, investment_amount):
        if investment_amount <= 0:
            st.error("Please enter a valid investment amount.")
            return

        if investment_amount > st.session_state.cash:
            st.error("Not enough cash to invest in this bond!")
            return

        if bond_name not in st.session_state.green_bonds:
            st.session_state.green_bonds[bond_name] = {"amount": 0, "active": True}

        st.session_state.green_bonds[bond_name]["amount"] += investment_amount
        st.session_state.cash -= investment_amount

        st.session_state.transactions.append({
            'round': st.session_state.round,
            'type': 'Invest in Green Bond',
            'bond_name': bond_name,
            'amount': investment_amount
        })
        st.success(f"✅ Successfully invested ${investment_amount:.2f} in {bond_name}.")

def withdraw_green_bond(bond_name):
    if bond_name not in st.session_state.green_bonds:
        st.error(f"You don't have any investment in {bond_name}!")
        return

    if not st.session_state.green_bonds[bond_name]["active"]:
        st.error(f"Investment in {bond_name} is already withdrawn.")
        return

    # Get the principal amount
    principal_amount = st.session_state.green_bonds[bond_name]["amount"]

    # Add the principal amount back to the cash balance
    st.session_state.cash += principal_amount

    # Mark the bond as inactive
    st.session_state.green_bonds[bond_name]["active"] = False

    # Record the transaction
    st.session_state.transactions.append({
        'round': st.session_state.round,
        'type': 'Withdraw Green Bond',
        'bond_name': bond_name,
        'amount': principal_amount
    })

    st.success(f"✅ Successfully withdrew ${principal_amount:.2f} from {bond_name}.")

def calculate_green_bond_interest():
    if st.session_state.round in [6, 7]:
        total_interest = 0
        for bond, details in st.session_state.green_bonds.items():
            if details["active"]:
                coupon_rate = GREEN_BONDS[bond]["coupon_rate"] / 100
                total_interest += details["amount"] * coupon_rate
        st.session_state.green_bond_interest = total_interest
        st.session_state.cash += total_interest
        st.success(f"✅ Interest of ${total_interest:.2f} added to your cash balance.")

def enforce_green_bond_rule():
    starting_cash = 10000000000  # Starting cash in hand
    required_investment = 0.15 * starting_cash
    total_green_bond_investment = sum(
        details["amount"] for details in st.session_state.green_bonds.values() if details["active"]
    )

    if total_green_bond_investment < required_investment:
        st.error("❌ You must invest at least 15% of your starting cash in green bonds!")
        st.write(f"Required Investment: ${required_investment:.2f}")
        st.write(f"Your Investment: ${total_green_bond_investment:.2f}")

        # Options for the user
        option = st.radio("Choose an option:", ["Sell Shares", "Take Loan", "Pay Penalty"])
        if option == "Sell Shares":
            st.write("Sell shares to meet the 15% requirement.")
            # Implement share selling logic here
        elif option == "Take Loan":
            loan_amount = required_investment - total_green_bond_investment
            st.session_state.loan_taken += loan_amount
            st.session_state.cash += loan_amount
            st.success(f"✅ Loan of ${loan_amount:.2f} taken to meet the requirement.")
        elif option == "Pay Penalty":
            penalty = 250000000  # 250 million rupees
            st.session_state.cash -= penalty
            st.error(f"❌ Penalty of ${penalty:.2f} deducted from your cash balance.")
    else:
        st.success("✅ You have met the 15% green bond investment requirement.")
    
def get_current_price(ticker):
    current_round = f"Round {st.session_state.round}"
    
    # Check for stock prices
    current_prices = st.session_state.companies[current_round]
    for country, companies in current_prices.items():
        if ticker in companies:
            return companies[ticker]
    
    # Check for forex prices
    if current_round in st.session_state.forex_data:
        forex_data = st.session_state.forex_data[current_round]
        if ticker in forex_data:
            return forex_data[ticker]['exchange_rate']
    
    # Check for derivative prices
    if current_round in st.session_state.derivatives_data:
        futures_data = st.session_state.derivatives_data[current_round].get('Future', {})
        if ticker in futures_data:
            return futures_data[ticker]['price']
    
    return 0  # Default if ticker not found in any category

def update_user_metrics(user_id):
    # Fetch latest metrics from Supabase
    latest_metrics = fetch_latest_user_metrics(user_id)
    
    if latest_metrics:
        cash_balance = latest_metrics['cash_balance']
    else:
        cash_balance = st.session_state.cash
    
    # Calculate total PNL
    total_pnl = calculate_total_pnl(user_id)
    
    # Update or insert into user_metrics table
    if latest_metrics:
        # Update existing entry
        conn.client.from_("user_metrics").update({
            "cash_balance": cash_balance,
            "total_pnl": total_pnl,
            "latest_round": st.session_state.round
        }).eq("user_id", user_id).execute()
    else:
        # Insert new entry
        conn.client.from_("user_metrics").insert({
            "user_id": user_id,
            "team_name": st.session_state.user['team_name'],
            "cash_balance": cash_balance,
            "total_pnl": total_pnl,
            "latest_round": st.session_state.round
        }).execute()

def fetch_latest_user_metrics(user_id):
    response = conn.client.from_("user_metrics").select("*").eq("user_id", user_id).execute()
    
    if response.data:
        return response.data[0]
    else:
        return None

def calculate_total_pnl(user_id):
    # Fetch all positions for the user
    positions_response = conn.client.from_("positions").select("*").eq("user_id", user_id).execute()
    
    if positions_response.data:
        positions_df = pd.DataFrame(positions_response.data)
        total_pnl = positions_df['pnl'].sum()
        return total_pnl
    else:
        return 0

def buy_insider_hint(insider_name):
    if insider_name in st.session_state.insider_purchases.get(f"Round {st.session_state.round}", []):
        st.error("You have already purchased this hint!")
        return

    insider_details = INSIDERS_LEVEL_4[insider_name]
    if insider_details["cost"] > st.session_state.cash:
        st.error("Not enough cash to buy this hint!")
        return

    st.session_state.cash -= insider_details["cost"]
    st.session_state.transactions.append({
        'round': st.session_state.round,
        'type': 'Buy Insider Hint',
        'insider': insider_name,
        'cost': insider_details["cost"],
        'hint': insider_details["hint"]
    })
    st.session_state.insider_purchases.setdefault(f"Round {st.session_state.round}", []).append(insider_name)
    st.success(f"✅ Hint purchased from {insider_name}!")
    st.rerun()

def calculate_positions(user_id):
    # Fetch all orders for the user from Supabase
    try:
        # Optimized query with specific columns and timeout
        orders_response = conn.client.from_("orders") \
            .select("id,user_id,security_type,quantity,price,order_type") \
            .eq("user_id", user_id) \
            .execute()  # 10-second timeout
        
        if not orders_response.data:
            return {}

        positions = {}

        # Process each order to calculate net positions
        for order in orders_response.data:
            ticker = order['ticker']
            quantity = order['lots'] * 10000
            price = order['price']
            order_type = order['type']

            if ticker not in positions:
                positions[ticker] = {
                    'long_quantity': 0,
                    'long_total_cost': 0.0,
                    'short_quantity': 0,
                    'short_total_value': 0.0
                }

            pos = positions[ticker]

            # Handle each order type explicitly
            if order_type == "Buy":
                if pos['short_quantity'] > 0:
                    cover_qty = min(quantity, pos['short_quantity'])
                    avg_short_price = pos['short_total_value'] / pos['short_quantity']
                    pos['short_quantity'] -= cover_qty
                    pos['short_total_value'] -= avg_short_price * cover_qty
                    remaining_qty = quantity - cover_qty
                    if remaining_qty > 0:
                        pos['long_quantity'] += remaining_qty
                        pos['long_total_cost'] += remaining_qty * price
                else:
                    pos['long_quantity'] += quantity
                    pos['long_total_cost'] += quantity * price

            elif order_type == "Sell":
                if pos['long_quantity'] >= quantity:
                    avg_long_price = pos['long_total_cost'] / pos['long_quantity']
                    pos['long_quantity'] -= quantity
                    pos['long_total_cost'] -= avg_long_price * quantity
                else:
                    extra_short_qty = quantity - pos['long_quantity']
                    avg_long_price = (pos['long_total_cost'] / pos['long_quantity']) if pos['long_quantity'] > 0 else price
                    # Sell all long holdings first
                    pos['long_quantity'] = 0
                    pos['long_total_cost'] = 0.0
                    # Remaining becomes short position
                    pos['short_quantity'] += extra_short_qty
                    pos['short_total_value'] += extra_short_qty * price

            elif order_type == "Short Sell":
                pos['short_quantity'] += quantity
                pos['short_total_value'] += quantity * price

            elif order_type == "Cover Short":
                if pos['short_quantity'] >= quantity:
                    avg_short_price = pos['short_total_value'] / pos['short_quantity']
                    pos['short_quantity'] -= quantity
                    pos['short_total_value'] -= avg_short_price * quantity
                else:
                    extra_long_qty = quantity - pos['short_quantity']
                    avg_short_price = (pos['short_total_value'] / pos['short_quantity']) if pos['short_quantity'] > 0 else price
                    # Cover entire short position first
                    pos['short_quantity'] = 0
                    pos['short_total_value'] = 0.0
                    # Remaining becomes long position
                    pos['long_quantity'] += extra_long_qty
                    pos['long_total_cost'] += extra_long_qty * price

        team_name = st.session_state.user.get('team_name', 'Unknown')

        # Write calculated positions back to Supabase table "positions"
        for ticker, data in positions.items():
            current_price = get_current_price(ticker)
            if current_price <= 0:
                st.error(f"Invalid price for {ticker}, position update skipped")
                continue

            # Cap long positions
            if data["long_quantity"] > 0:
                current_long_value = data["long_quantity"] * current_price
                if current_long_value > 1e9:
                    max_qty = int(1e9 // current_price)
                    if max_qty <= 0:
                        data["long_quantity"] = 0
                        data["long_total_cost"] = 0
                    else:
                        ratio = max_qty / data["long_quantity"]
                        data["long_quantity"] = max_qty
                        data["long_total_cost"] *= ratio
                    st.error(f"Long position in {ticker} capped at $1B")

            # Cap short positions
            if data["short_quantity"] > 0:
                current_short_value = data["short_quantity"] * current_price
                if current_short_value > 1e9:
                    max_qty = int(1e9 // current_price)
                    if max_qty <= 0:
                        data["short_quantity"] = 0
                        data["short_total_value"] = 0
                    else:
                        ratio = max_qty / data["short_quantity"]
                        data["short_quantity"] = max_qty
                        data["short_total_value"] *= ratio
                    st.error(f"Short position in {ticker} capped at $1B")
            
            
            # Handle Long Positions
            if data["long_quantity"] > 0:
                avg_long_price = data["long_total_cost"] / data["long_quantity"]
                current_price = get_current_price(ticker)
                pnl = (current_price - avg_long_price) * data["long_quantity"]
                existing_long_resp = conn.client.from_("positions").select("*")\
                                    .eq("user_id", user_id).eq("ticker", ticker).eq("position_type", "long").execute()
                if existing_long_resp.data:
                    conn.client.from_("positions").update({
                        "quantity": data["long_quantity"],
                        "avg_price": avg_long_price,
                        "pnl": pnl,
                        "team_name": team_name,
                    }).eq("user_id", user_id).eq("ticker", ticker).eq("position_type", "long").execute()
                else:
                    conn.client.from_("positions").insert({
                        "user_id": user_id,
                        "team_name": team_name,
                        "ticker": ticker,
                        "quantity": data["long_quantity"],
                        "avg_price": avg_long_price,
                        "pnl": pnl,
                        "position_type": "long"
                    }).execute()
            else:
                # Remove long position entry if no longer exists
                conn.client.from_("positions").delete()\
                            .eq("user_id", user_id).eq("ticker", ticker).eq("position_type", "long").execute()

            # Handle Short Positions
            if data["short_quantity"] > 0:
                avg_short_price = data["short_total_value"] / data["short_quantity"]
                current_price = get_current_price(ticker)
                pnl = (avg_short_price - current_price) * data["short_quantity"]
                existing_short_resp = conn.client.from_("positions").select("*")\
                                    .eq("user_id", user_id).eq("ticker", ticker).eq("position_type", "short").execute()
                if existing_short_resp.data:
                    conn.client.from_("positions").update({
                        "quantity": data["short_quantity"],
                        "avg_price": avg_short_price,
                        "pnl": pnl,
                        "team_name": team_name,
                    }).eq("user_id", user_id).eq("ticker", ticker).eq("position_type", "short").execute()
                else:
                    conn.client.from_("positions").insert({
                        "user_id": user_id,
                        "team_name": team_name,
                        "ticker": ticker,
                        "quantity": data["short_quantity"],
                        "avg_price": avg_short_price,
                        "pnl": pnl,
                        "position_type": "short"
                    }).execute()
            else:
                # Remove short position entry if no longer exists
                conn.client.from_("positions").delete()\
                            .eq("user_id", user_id).eq("ticker", ticker).eq("position_type", "short").execute()

        return positions
    except Exception as e:
        st.error(f"Database operation failed: {str(e)}")
        st.rerun()  # Auto-recover on error
        return {}


def display_orders_and_positions():
    user_id = st.session_state.user_id
    
    # Fetch orders
    orders_response = conn.client.from_("orders").select("*").eq("user_id", user_id).execute()
    
    if orders_response.data:
        orders_df = pd.DataFrame(orders_response.data)
        
        # Include STT in the transaction summary
        st.subheader("📝 Transaction Summary")
        st.write(orders_df[['type', 'ticker', 'lots', 'price', 's31_fees', 'round']])
    else:
        st.info("No orders found.")

    # Fetch and display positions from the same table
    calculate_positions(st.session_state.user_id)

    positions_response = conn.client.from_("positions").select("*").eq("user_id", user_id).execute()

    if positions_response.data:
        positions_df = pd.DataFrame(positions_response.data)

        # Separate long and short positions using the type column
        long_positions = positions_df[positions_df['position_type'] == 'long']
        short_positions = positions_df[positions_df['position_type'] == 'short']

        st.subheader("Long Positions")
        st.write(long_positions[['ticker', 'quantity', 'avg_price', 'pnl']])

        st.subheader("Short Positions")
        st.write(short_positions[['ticker', 'quantity', 'avg_price', 'pnl']])
    else:
        st.info("No positions found.")


initialize_session()

def record_transaction(order_type, ticker, quantity, price,stt, asset_type='stock'):
    user_id = st.session_state.user_id
    team_name = st.session_state.user['team_name']
    
    # Check if user exists
    user_response = conn.client.from_("users").select("*").eq("id", user_id).execute()
    
    if not user_response.data:
        st.error(f"User with ID {user_id} does not exist.")
        return
    
    # Proceed with recording transaction
    if asset_type == 'forex':
        # Handle Forex transaction
        conn.client.from_("forex_transactions").insert([
            {
                "user_id": user_id,
                "team_name": team_name,
                "type": order_type,
                "currency": ticker,
                "amount": quantity,
                "exchange_rate": price,
                "round": st.session_state.round,
                "s31_fees": stt
            }
        ]).execute()
        
    else:
        # Handle stock transaction
        conn.client.from_("orders").insert([
            {
                "user_id": user_id,
                "team_name": team_name,
                "type": order_type,
                "ticker": ticker,
                "lots": quantity,
                "price": price,
                "round": st.session_state.round,
                "s31_fees": stt
            }
        ]).execute()
    
    calculate_positions(user_id)
    #update_user_metrics(user_id)


ROUND_PASSWORDS = {
    2: "BULLISHVIBES",
    3: "CAPITALCHAOS",
    4: "LOSTINLIQUIDITY",
    5: "NOMOREDEBT",
    6: "DEBTTRAP",
    7: "RISKITALL"
}

GREEN_BONDS = {
    "India - Bharat Green Infrastructure Bond (BGIB-2035)": {
        "country": "India",
        "amount": 6000000000,  # $6 billion
        "tenure": 10,
        "maturity": 2035,
        "coupon_rate": 5.75,
        "listed_on": ["BSE", "SGX"],
        "rating": {"CRISIL": "A+", "Moody's": "A+"}
    },
    "Singapore - SG Green Future Bond (SG-GFB-2033)": {
        "country": "Singapore",
        "amount": 5500000000,  # $5.5 billion
        "tenure": 8,
        "maturity": 2033,
        "coupon_rate": 4.25,
        "listed_on": ["SGX"],
        "rating": {"Fitch": "AAA", "S&P": "AAA"}
    },
    "Russia - Siberian Renewable Energy Bond (SREB-2040)": {
        "country": "Russia",
        "amount": 5000000000,  # $5 billion
        "tenure": 15,
        "maturity": 2040,
        "coupon_rate": 6.50,
        "listed_on": ["MOEX", "LSE"],
        "rating": {"S&P": "BBB+", "Moody's": "BBB+"}
    },
    "China - Dragon Sustainability Bond (DSB-2038)": {
        "country": "China",
        "amount": 7500000000,  # $7.5 billion
        "tenure": 12,
        "maturity": 2038,
        "coupon_rate": 5.90,
        "listed_on": ["SSE", "HKEX"],
        "rating": {"China Bond Rating Agency": "A", "Moody's": "A"}
    },
    "Japan - Nippon Green Innovation Bond (NGIB-2045)": {
        "country": "Japan",
        "amount": 6800000000,  # $6.8 billion
        "tenure": 20,
        "maturity": 2045,
        "coupon_rate": 3.80,
        "listed_on": ["TSE", "NYSE"],
        "rating": {"Japan Credit Rating Agency": "AA", "Fitch": "AA"}
    }
}

INSIDERS_LEVEL_4 = {
    "Vladimir “The Ghost” Petroski": {
        "cost": 285750000,
        "hint": """
        “Beneath its dominance, Rosneft may be grappling with mounting pressure that could threaten its future. 
        Western sanctions are tightening, restricting access to cutting-edge oil extraction tech and critical financing. 
        Meanwhile, China and India—key buyers—are demanding steeper discounts, squeezing profit margins.

        Internally, aging infrastructure and rising production costs are adding strain, while geopolitical instability 
        threatens supply routes. If these pressures escalate, could Rosneft’s grip on global energy markets start to slip? 
        The cracks are showing.”
        """
    },
    "Jack Mamamia": {
        "cost": 254620000,
        "hint": """
        “Mizuho Financial Group may be standing on dangerously thin ice. We warn that the bank’s exposure to highly 
        leveraged Japanese conglomerates is reaching precarious levels, while a weakening yen intensifies offshore debt risks. 
        Moreover, Mizuho’s reliance on Japan’s ultra-low interest rate environment—a fragile crutch that could shatter if 
        the Bank of Japan shifts policy.

        If rate hikes materialize, Mizuho’s balance sheet could unravel with shocking speed, triggering liquidity shocks, 
        asset sell-offs, and systemic ripple effects across Japan’s financial sector.”
        """
    },
    "Binga Singh Aloowalia": {
        "cost": 271780000,
        "hint": """
        “Behind closed doors, Indian Oil Corp (IOC) may be faced with a financial and operational storm far worse than it appears. 
        Insiders whisper of crippling refining margins, unsustainable subsidy burdens, and mounting debt pressures. 
        With global crude prices volatile and government price controls squeezing profits, IOC’s cash flow could be nearing 
        a breaking point. If a liquidity crunch hits, India’s largest refiner could be sleepwalking into an energy crisis.”
        """
    },
    "Roaring Kitty": {
        "cost": 269420000,
        "hint": """
        “China’s Hua Hong Semiconductor may be staring down a brutal convergence of threats—and survival won’t be easy. 
        U.S. tariffs and sanctions are tightening the noose, choking off access to critical chip making equipment, 
        while Taiwanese giants like TSMC and UMC outpace Hua Hong in both technology and scale.

        Even worse? China’s domestic demand slump and Beijing’s costly subsidies can’t mask Hua Hong’s widening competitive gap. 
        As geopolitical pressures mount and cutting-edge nodes remain out of reach, is Hua Hong doomed to fall further behind 
        in the global chip race? The cracks are showing.”
        """
    },
    "Jim Crammer": {
        "cost": 221500000,
        "hint": """
        “Hyphens Pharma International is gaining momentum, with a 22.1% revenue surge in 2024, fueled by strong sales in 
        Singapore and Malaysia. A S$6M investment from Metro Holdings in its digital healthtech unit underscores its expansion 
        into high-growth sectors.

        With a 46% stock gain over five years and strategic moves in digital healthcare, Hyphens Pharma is strengthening 
        its market position. As the company continues to innovate, investors should keep a close watch.”
        """
    }
}


# ---- Login Screen ----
st.title(f"Bulls v/s Borders - Round {st.session_state.round}")

if st.session_state["user"] is None:
    st.subheader("🔐 Login")

    team_name = st.text_input("Team Name", key="team_name")
    password = st.text_input("Password", type="password", key="password")

    if st.button("Login"):
        try:
            # Query Supabase for user authentication
            response = conn.client.from_("users").select("id, team_name, password").eq("team_name", team_name).single().execute()

            if response.data and response.data["password"] == password:
                st.session_state["user"] = response.data
                st.session_state["user_id"] = response.data["id"]
                st.success(f"✅ Logged in as {response.data['team_name']}")
                st.rerun()  # Refresh after login
            else:
                st.error("❌ Invalid team name or password.")

        except Exception as e:
            st.error(f"Login failed: {e}")

# ---- If Logged In, Show Order Form ----
else:
    st.success(f"✅ Logged in as {st.session_state['user']['team_name']}")
    
    user_id = st.session_state.user_id
    
    latest_metrics = fetch_latest_user_metrics(user_id)
    
    
    if latest_metrics:
        cash_balance = latest_metrics['cash_balance']
        total_pnl = latest_metrics['total_pnl']
        latest_round = latest_metrics['latest_round']
    else:
        # Handle the case where no data exists for the user
        cash_balance = st.session_state.cash
        total_pnl = 0
        latest_round = 1
    
    def process_futures_expiry():
        current_round = st.session_state.round
        expired_futures = []

        for key, data in list(st.session_state.derivatives.items()):
            parts = key.split("_")
            if len(parts) == 3:  # Format: <CompanyName>_Fut_<Expiry>
                company = parts[0]
                expiry_round = int(parts[2][1:])

                if expiry_round == current_round:
                    round_key = f"Round {current_round}"
                    future_data = st.session_state.derivatives_data.get(round_key, {}).get("Future", {}).get(key)

                    if not future_data or 'price' not in future_data:
                        st.error(f"Price data missing for {key} in Round {current_round}.")
                        continue

                    settlement_price = future_data['price']
                    contract_size = future_data.get('contract_size', 10000)
                    original_price = data['price']

                    # Handle long positions
                    if company in st.session_state.derivatives:
                        long_contracts = data['contracts']
                        
                        # Deduct remaining 75% margin
                        remaining_margin = long_contracts * original_price * contract_size * 0.75
                        st.session_state.cash -= remaining_margin
                        
                        # Calculate and settle PNL
                        pnl = (settlement_price - original_price) * long_contracts * contract_size
                        st.session_state.cash += pnl

                        # Remove long position after settlement
                        del st.session_state.derivatives[key]

                        # Record transaction for settlement of long position
                        record_transaction('Settle Long Future', company, long_contracts, settlement_price)
                    
                    # Handle short positions
                    elif company in st.session_state.short_positions:
                        short_data = st.session_state.short_positions[company]
                        short_contracts = short_data['contracts']
                        
                        # Deduct remaining 75% margin
                        remaining_margin = short_contracts * original_price * contract_size * 0.75
                        st.session_state.cash -= remaining_margin
                        
                        # Calculate and settle PNL
                        pnl = (original_price - settlement_price) * short_contracts * contract_size
                        st.session_state.cash += pnl

                        # Remove short position after settlement
                        del st.session_state.short_positions[company]

                        # Record transaction for settlement of short position
                        record_transaction('Settle Short Future', company, short_contracts, settlement_price)

                    expired_futures.append(company)

        if expired_futures:
            st.success(f"✅ Futures expired and settled for: {', '.join(expired_futures)}")
        else:
            st.info("No futures expired in this round.")

    # Display current round number
    st.write(f"Current Round: {st.session_state.round}")
    
    # Function to calculate STT
    def calculate_stt(transaction_type, transaction_value):
        stt_rates = {
            'equity': 0.001, 
            'forex': 0.001,  
            'derivatives': 0.001,
            'commodities':0.001
        }
        return transaction_value * stt_rates.get(transaction_type, 0)
    
    
    # Core transaction functions
    
    def buy_shares(company, shares, current_price, country):
        if shares <= 0:
            st.error("Please enter a valid number of shares to buy.")
            return

        # Check if there is an open short position for the given company
        if company in st.session_state.short_positions and st.session_state.short_positions[company]['shares'] > 0:
            short_data = st.session_state.short_positions[company]
            # Determine how many shorted shares to cover
            shares_to_cover = min(shares, short_data['shares'])
            cover_value = shares_to_cover * current_price * 10000  # Total cost/value involved in covering shorts

            # Calculate STT if needed (you may keep it or adjust accordingly)
            stt = calculate_stt('equity', cover_value)
            # Instead of reducing cash for a buy, add the cover value to cash
            st.session_state.cash += cover_value - (3 * stt)
            st.success(f"💰 ${cover_value:.2f} added to your cash balance for covering {shares_to_cover} shorted shares of {company}!")
            # Update the short position by reducing the number of shares and adjusting the total short value
            # (Ensure you update the logic as per your requirements; this is a basic example)
            short_data['shares'] -= shares_to_cover
            # We use a simple proportional reduction for short_value. Be cautious if dividing by zero.
            if short_data['shares'] > 0:
                reduction = shares_to_cover * (short_data['short_value'] / (short_data['shares'] + shares_to_cover))
                short_data['short_value'] -= reduction
            else:
                # Remove the company from short positions if fully covered
                del st.session_state.short_positions[company]
            
            # Record the covering transaction
            record_transaction('Cover Short', company, shares, current_price,stt)
            st.rerun()
            # If the user wants to buy more shares beyond covering the short, process as a normal buy order
            remaining_shares = shares - shares_to_cover
            if remaining_shares > 0:
                total_cost = remaining_shares * current_price * 10000
                stt = calculate_stt('equity', total_cost)
                total_cost_with_stt = total_cost + stt
                if total_cost_with_stt > st.session_state.cash:
                    st.error("Not enough cash to buy the remaining shares after covering the short!")
                    return
                if company not in st.session_state.portfolio:
                    st.session_state.portfolio[company] = {
                        'shares': 0,
                        'total_spent': 0,
                        'total_stt': 0,
                        'country': country
                    }
                st.session_state.portfolio[company]['shares'] += remaining_shares
                st.session_state.portfolio[company]['total_spent'] += total_cost
                st.session_state.portfolio[company]['total_stt'] += stt
                st.session_state.cash -= total_cost_with_stt
                record_transaction('Buy', company, shares, current_price,stt)
                st.success(f"✅ Successfully bought {remaining_shares} shares of {company}!")
                st.rerun()

        else:
            # Normal buy flow (if no short position to cover)
            total_cost = shares * current_price * 10000
            stt = calculate_stt('equity', total_cost)
            total_cost_with_stt = total_cost + stt
            if total_cost_with_stt > st.session_state.cash:
                st.error("Not enough cash to buy these shares!")
                return
            if company not in st.session_state.portfolio:
                st.session_state.portfolio[company] = {
                    'shares': 0,
                    'total_spent': 0,
                    'total_stt': 0,
                    'country': country
                }
            st.session_state.portfolio[company]['shares'] += shares
            st.session_state.portfolio[company]['total_spent'] += total_cost
            st.session_state.portfolio[company]['total_stt'] += stt
            st.session_state.cash -= total_cost_with_stt
            record_transaction('Buy', company, shares, current_price,stt)
            
            st.success(f"✅ Successfully bought {shares} shares of {company}!")
            st.rerun()

    def sell_shares(company, shares, current_price):
        if shares <= 0:
            st.error("Please enter a valid number of shares to sell.")
            return

        if company not in st.session_state.portfolio:
            # Treat as short sell
            if company not in st.session_state.short_positions:
                st.session_state.short_positions[company] = {
                    'shares': 0,
                    'short_price': 0,
                    'short_value': 0
                }
            
            # Record short sell
            short_shares = shares
            short_value = short_shares * current_price * 10000
            
            st.session_state.short_positions[company]['shares'] += short_shares
            st.session_state.short_positions[company]['short_price'] += short_value
            st.session_state.short_positions[company]['short_value'] += short_value
            
            # Deduct cash immediately
            total_received = short_value
            stt = calculate_stt('equity', total_received)
            total_received_after_stt = total_received - stt
            
            st.session_state.cash -= total_received_after_stt
            record_transaction('Short Sell', company, shares, current_price,stt)
            st.success(f"✅ Successfully short sold {short_shares} shares of {company}! (STT: ${stt:.2f})")
            st.rerun()
        
        else:
            company_data = st.session_state.portfolio[company]
            if company_data['shares'] < shares:
                st.error(f"You don't own enough shares of {company} to sell!")
                return

            total_received = shares * current_price * 10000
            stt = calculate_stt('equity', total_received)
            total_received_after_stt = total_received - stt

            company_data['shares'] -= shares
            company_data['total_spent'] += total_received
            company_data['total_stt'] += stt
            st.session_state.cash += total_received_after_stt

            if company_data['shares'] <= 0:
                del st.session_state.portfolio[company]

            record_transaction('Sell', company, shares, current_price,stt)
            st.success(f"✅ Successfully sold {shares} shares of {company}! (STT: ${stt:.2f})")
            st.rerun()

    # IPO and Forex functions
    
    def buy_forex(currency, amount):
        if amount <= 0:
            st.error("Please enter a valid amount to buy.")
            return

        current_round_forex = st.session_state.forex_data[f"Round {st.session_state.round}"]
        exchange_rate = current_round_forex[currency]['exchange_rate']

        # Check if there is an open short position for the given currency
        if currency in st.session_state.short_positions and st.session_state.short_positions[currency]['amount'] > 0:
            short_data = st.session_state.short_positions[currency]
            # Determine how much shorted amount to cover
            amount_to_cover = min(amount, short_data['amount'])
            cover_value = amount_to_cover * exchange_rate * 10000  # Total cost/value involved in covering shorts

            # Calculate STT if needed
            stt = calculate_stt('forex', cover_value)
            # Instead of reducing cash for a buy, add the cover value to cash
            st.session_state.cash += cover_value - (3 * stt)
            st.success(f"💰 ${cover_value:.2f} added to your cash balance for covering {amount_to_cover} shorted {currency}!")

            # Update the short position by reducing the amount and adjusting the total short value
            short_data['amount'] -= amount_to_cover
            if short_data['amount'] > 0:
                reduction = amount_to_cover * (short_data['short_value'] / (short_data['amount'] + amount_to_cover))
                short_data['short_value'] -= reduction
            else:
                # Remove the currency from short positions if fully covered
                del st.session_state.short_positions[currency]

            # Record the covering transaction
            record_transaction('Cover Short', currency, amount_to_cover, exchange_rate, stt)
            st.rerun()

            # If the user wants to buy more forex beyond covering the short, process as a normal buy order
            remaining_amount = amount - amount_to_cover
            if remaining_amount > 0:
                total_cost = remaining_amount * exchange_rate * 10000
                stt = calculate_stt('forex', total_cost)
                total_cost_with_stt = total_cost + stt
                if total_cost_with_stt > st.session_state.cash:
                    st.error("Not enough cash to buy the remaining forex after covering the short!")
                    return
                if currency not in st.session_state.forex:
                    st.session_state.forex[currency] = {'amount': 0, 'total_spent': 0, 'total_stt': 0}
                st.session_state.forex[currency]['amount'] += remaining_amount
                st.session_state.forex[currency]['total_spent'] += total_cost
                st.session_state.forex[currency]['total_stt'] += stt
                st.session_state.cash -= total_cost_with_stt
                record_transaction('Buy', currency, remaining_amount, exchange_rate, stt)
                st.success(f"✅ Successfully bought {remaining_amount} {currency}!")
                st.rerun()

        else:
            # Normal buy flow (if no short position to cover)
            total_cost = amount * exchange_rate * 10000
            stt = calculate_stt('forex', total_cost)
            total_cost_with_stt = total_cost + stt

            if total_cost_with_stt > st.session_state.cash:
                st.error("Not enough cash to buy this currency!")
                return

            if currency not in st.session_state.forex:
                st.session_state.forex[currency] = {'amount': 0, 'total_spent': 0, 'total_stt': 0}

            st.session_state.forex[currency]['amount'] += amount
            st.session_state.forex[currency]['total_spent'] += total_cost
            st.session_state.forex[currency]['total_stt'] += stt
            st.session_state.cash -= total_cost_with_stt

            record_transaction('Buy', currency, amount, exchange_rate, stt)
            st.success(f"✅ Successfully bought {amount} {currency}! (STT: ${stt:.2f})")
            st.rerun()


    def sell_forex(currency, amount):
        if amount <= 0:
            st.error("Please enter a valid amount to sell.")
            return

        current_round_forex = st.session_state.forex_data[f"Round {st.session_state.round}"]
        exchange_rate = current_round_forex[currency]['exchange_rate']

        # Check if there is an open long position for the given currency
        if currency in st.session_state.forex and st.session_state.forex[currency]['amount'] > 0:
            forex_data = st.session_state.forex[currency]
            
            # Determine how much to sell
            amount_to_sell = min(amount, forex_data['amount'])
            total_received = amount_to_sell * exchange_rate * 10000

            # Calculate STT if needed
            stt = calculate_stt('forex', total_received)
            
            # Add cash for selling
            st.session_state.cash += total_received - stt

            # Update the long position by reducing the amount
            forex_data['amount'] -= amount_to_sell

            # Remove currency from long positions if fully sold
            if forex_data['amount'] <= 0:
                del st.session_state.forex[currency]

            # Record the selling transaction
            record_transaction('Sell', currency, amount_to_sell, exchange_rate,stt)
            st.success(f"✅ Successfully sold {amount_to_sell} {currency}!")
            
            # If the user wants to short sell more forex beyond selling the long position, process as a short sell order
            remaining_amount = amount - amount_to_sell
            if remaining_amount > 0:
                # Treat as short sell
                total_received = remaining_amount * exchange_rate * 10000
                stt = calculate_stt('forex', total_received)
                total_received_after_stt = total_received - stt
                
                # Deduct cash immediately (for short selling, cash is not received but rather used as collateral)
                st.session_state.cash -= total_received_after_stt
                
                if currency not in st.session_state.short_positions:
                    st.session_state.short_positions[currency] = {
                        'amount': 0,
                        'short_value': 0
                    }
                
                st.session_state.short_positions[currency]['amount'] += remaining_amount
                st.session_state.short_positions[currency]['short_value'] += total_received
                
                # Record the short selling transaction
                record_transaction('Short Sell', currency, remaining_amount, exchange_rate,stt)
                st.success(f"✅ Successfully short sold {remaining_amount} {currency}! (STT: ${stt:.2f})")
                st.rerun()
        else:
            # Normal short sell flow (if no long position to sell)
            # Treat as short sell
            total_received = amount * exchange_rate * 10000
            stt = calculate_stt('forex', total_received)
            total_received_after_stt = total_received - stt
            
            # Deduct cash immediately (for short selling, cash is not received but rather used as collateral)
            st.session_state.cash -= total_received_after_stt
            
            if currency not in st.session_state.short_positions:
                st.session_state.short_positions[currency] = {
                    'amount': 0,
                    'short_value': 0
                }
            
            st.session_state.short_positions[currency]['amount'] += amount
            st.session_state.short_positions[currency]['short_value'] += total_received
            
            # Record the short selling transaction
            record_transaction('Short Sell', currency, amount, exchange_rate,stt)
            st.success(f"✅ Successfully short sold {amount} {currency}! (STT: ${stt:.2f})")
            st.rerun()

    def buy_derivative(company, contracts):
        """
        Handles buying futures contracts. Supports covering short positions and normal buying flow.
        """
        if contracts <= 0:
            st.error("Please enter a valid number of contracts to buy.")
            return

        # Get current round and derivative details
        current_round_derivatives = st.session_state.derivatives_data[f"Round {st.session_state.round}"]
        if "Future" not in current_round_derivatives or company not in current_round_derivatives["Future"]:
            st.error("Invalid company selected.")
            return

        derivative_details = current_round_derivatives["Future"][company]
        current_price = derivative_details['price']
        contract_size = derivative_details['contract_size']

        # --- Cover Short Derivative Position (if exists) ---
        if company in st.session_state.short_positions and st.session_state.short_positions[company].get('contracts', 0) > 0:
            short_data = st.session_state.short_positions[company]

            # Determine how many shorted contracts to cover
            contracts_to_cover = min(contracts, short_data['contracts'])
            cover_value = contracts_to_cover * current_price * contract_size * 0.25  # Total value involved in covering shorts

            # Calculate STT for covering shorts
            stt = calculate_stt('derivatives', cover_value)

            # Increase cash instead of reducing it when covering shorts
            st.session_state.cash += cover_value - (3 * stt)

            st.success(f"💰 ${cover_value:.2f} added to your cash balance from covering {contracts_to_cover} shorted Future contracts for {company}!")

            # Update the short position: reduce contracts and adjust short value proportionally
            if short_data['contracts'] > contracts_to_cover:
                reduction = contracts_to_cover * (short_data['short_value'] / short_data['contracts'])
                short_data['contracts'] -= contracts_to_cover
                short_data['short_value'] -= reduction
            else:
                # Remove short position if fully covered
                del st.session_state.short_positions[company]

            # Record the covering transaction
            record_transaction('Cover Short', company, contracts, current_price,stt)

            # Reduce the requested contracts by the number already covered
            contracts -= contracts_to_cover

            # If all contracts were used to cover shorts, refresh UI and exit
            if contracts <= 0:
                st.rerun()

        # --- Normal Buy Flow for Remaining Contracts ---
        total_cost = contracts * current_price * contract_size * 0.25  # Margin requirement applies here
        stt = calculate_stt('derivatives', total_cost)
        total_cost_with_stt = total_cost + stt

        if total_cost_with_stt > st.session_state.cash:
            st.error("Not enough cash to buy these futures contracts!")
            return

        # Update derivatives holdings
        if company not in st.session_state.derivatives:
            st.session_state.derivatives[company] = {'contracts': 0, 'total_spent': 0, 'margin_required': 0, 'price': current_price}

        st.session_state.derivatives[company]['contracts'] += contracts
        st.session_state.derivatives[company]['total_spent'] += total_cost
        st.session_state.derivatives[company]['margin_required'] += total_cost

        # Deduct cash and record transaction
        st.session_state.cash -= total_cost_with_stt
        record_transaction('Buy', company, contracts, current_price,stt)

        st.success(f"✅ Successfully bought {contracts} Future contracts for {company}! (STT: ${stt:.2f})")
        st.rerun()

    def sell_derivative(company, contracts):
        if contracts <= 0:
            st.error("Please enter a valid number of contracts to sell.")
            return

        # Retrieve derivative details for validation
        current_round_derivatives = st.session_state.derivatives_data[f"Round {st.session_state.round}"]
        if "Future" not in current_round_derivatives or company not in current_round_derivatives["Future"]:
            st.error("Invalid company selected.")
            return

        derivative_details = current_round_derivatives["Future"][company]
        current_price = derivative_details['price']
        contract_size = derivative_details['contract_size']

        total_value = contracts * current_price * contract_size * 0.25  # 25% margin
        stt = calculate_stt('derivatives', total_value)

        # Check if user has existing long positions
        if company not in st.session_state.derivatives:
            # No existing long position: treat as short sell
            if company not in st.session_state.short_positions:
                st.session_state.short_positions[company] = {
                    'contracts': 0,
                    'short_value': 0
                }

            short_value = contracts * current_price * contract_size * 0.25  # Margin equivalent
            st.session_state.short_positions[company]['contracts'] += contracts
            st.session_state.short_positions[company]['short_value'] += short_value

            # Deduct cash immediately (collateral for short position)
            st.session_state.cash -= short_value

            record_transaction('Short Sell', company, contracts, current_price, stt)
            st.success(f"✅ Successfully short sold {contracts} Future contracts for {company}! (STT: ${stt:.2f})")
            st.rerun()

        else:
            # Existing long position: check if enough contracts to sell
            derivative_data = st.session_state.derivatives[company]

            if derivative_data['contracts'] < contracts:
                # Not enough long positions: Sell all long first, then short remaining
                contracts_to_short = contracts - derivative_data['contracts']
                contracts_to_sell = derivative_data['contracts']

                # Sell existing long positions first
                if contracts_to_sell > 0:
                    sell_value_long = contracts_to_sell * current_price * contract_size * 0.25
                    stt_long = calculate_stt('derivatives', sell_value_long)
                    st.session_state.cash += sell_value_long - stt_long

                    record_transaction('Sell', company, contracts_to_sell, current_price, stt_long)
                    del st.session_state.derivatives[company]

                    st.success(f"✅ Successfully sold {contracts_to_sell} Future contracts for {company}! (STT: ${stt_long:.2f})")

                # Now handle remaining as short sell
                short_value_extra = contracts_to_short * current_price * contract_size * 0.25

                if company not in st.session_state.short_positions:
                    st.session_state.short_positions[company] = {
                        'contracts': 0,
                        'short_value': 0
                    }

                st.session_state.short_positions[company]['contracts'] += contracts_to_short
                st.session_state.short_positions[company]['short_value'] += short_value_extra

                # Deduct cash immediately (collateral)
                st.session_state.cash -= short_value_extra

                record_transaction('Short Sell', company, contracts_to_short, current_price, calculate_stt('derivatives', short_value_extra))
                st.success(f"✅ Successfully short sold additional {contracts_to_short} Future contracts for {company}!")
                st.rerun()

            else:
                # Enough long positions exist: normal selling flow
                derivative_data['contracts'] -= contracts

                sell_value = total_value
                total_received_after_stt = sell_value - stt

                # Add cash after selling derivatives
                st.session_state.cash += total_received_after_stt

                if derivative_data['contracts'] == 0:
                    del st.session_state.derivatives[company]

                record_transaction('Sell', company, contracts, current_price, stt)
                st.success(f"✅ Successfully sold {contracts} Future contracts for {company}! (STT: ${stt:.2f})")
                st.rerun()


    def take_loan(amount):
        MAX_LOAN = 3_000_000_000  # $3 billion cap
        
        if amount <= 0:
            st.error("Please enter a valid loan amount.")
            return
        
        if amount > MAX_LOAN:
            st.error(f"Loan amount exceeds maximum allowed limit of $3B (Requested: ${amount/1e9:.2f}B)")
            return
        
        if st.session_state.loan['amount'] > 0:
            st.error("You already have an outstanding loan.")
            return
        
        # Track total loans across all rounds
        total_existing_loans = st.session_state.get('total_loans_taken', 0)
        if total_existing_loans + amount > MAX_LOAN:
            remaining = MAX_LOAN - total_existing_loans
            st.error(f"Can only borrow ${remaining:,.2f} more to stay under $3B cap")
            return
        
        st.session_state.loan['amount'] = amount
        st.session_state.loan['round_taken'] = st.session_state.round
        st.session_state.cash += amount
        
        # Update total loans tracking
        st.session_state.total_loans_taken = total_existing_loans + amount
        
        st.session_state.transactions.append({
            'round': st.session_state.round,
            'type': 'Take Loan',
            'amount': amount,
            'interest_rate': 0.15
        })
        
        st.success(f"""✅ Successfully took loan of ${amount/1e9:.2f}B
                Remaining borrowing capacity: ${(MAX_LOAN - st.session_state.total_loans_taken)/1e9:.2f}B""")
        st.rerun()
        
    def repay_loan():
        if st.session_state.loan['amount'] <= 0:
            st.error("You don't have any outstanding loan to repay.")
            return

        total_repayment = st.session_state.loan['amount'] * (1 + 0.15)
        if st.session_state.cash < total_repayment:
            st.error("Not enough cash to repay the loan.")
            return

        st.session_state.cash -= total_repayment
        st.session_state.loan['amount'] = 0
        st.session_state.loan['round_taken'] = None

        st.session_state.transactions.append({
            'round': st.session_state.round,
            'type': 'Repay Loan',
            'amount': total_repayment,
            'interest_rate': 0.15
        })
        st.success(f"✅ Successfully repaid the loan of ${total_repayment:.2f}.")
        
    # Streamlit app layout
    st.title("📈 Trading Platform")
    st.sidebar.write(f"💰 Cash in Hand ($): {st.session_state.cash:,.2f}")
    
    if st.session_state.round >= 4:
        st.sidebar.subheader("💵 Loan Management")
        loan_amount = st.sidebar.number_input("Loan Amount", min_value=0)
        if st.session_state.loan['amount'] <= 0:
            if st.sidebar.button("Take Loan"):
                take_loan(loan_amount)
        else:
            st.sidebar.write(f"Outstanding Loan: ${st.session_state.loan['amount']:.2f}")
            if st.sidebar.button("Repay Loan"):
                repay_loan()
    # Security Type Selection
    st.sidebar.subheader("📈 Trade Securities")
    selected_security = st.sidebar.selectbox(
        "Select security type to trade",
        ["Shares", "Forex", "Derivatives", "Green Bonds", "Insider"]
    )

    # Shares Trading Section
    if selected_security == "Shares":
        current_prices = st.session_state.companies[f"Round {st.session_state.round}"]
        all_companies = {}
        for country, companies in current_prices.items():
            all_companies[country] = list(companies.keys())
        
        
        country_selected = st.sidebar.selectbox(
            "Select Country", 
            list(all_companies.keys())
        )
        company_selected = st.sidebar.selectbox(
            "Select Company", 
            all_companies[country_selected]
        )
        shares = st.sidebar.number_input(f"Number of shares for {company_selected}", min_value=0)
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("Buy Shares"):
                buy_shares(company_selected, shares, current_prices[country_selected][company_selected], country_selected)
        with col2:
            if st.button("Sell Shares"):
                sell_shares(company_selected, shares, current_prices[country_selected][company_selected])
    
    # Forex Trading Section
    elif selected_security == "Forex":
        current_round_forex = st.session_state.forex_data[f"Round {st.session_state.round}"]
        currency_selected = st.sidebar.selectbox("Select Currency", list(current_round_forex.keys()))
        currency_details = current_round_forex[currency_selected]
        
        st.sidebar.write(f"**Currency:** {currency_details['currency']}")
        st.sidebar.write(f"**Exchange Rate:** ${currency_details['exchange_rate']}")
        
        forex_amount = st.sidebar.number_input(f"Amount of {currency_selected} to buy/sell", min_value=0)
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("Buy Forex"):
                buy_forex(currency_selected, forex_amount)
        with col2:
            if st.button("Sell Forex"):
                sell_forex(currency_selected, forex_amount)

    # Derivatives Trading Section
    elif selected_security == "Derivatives":
        current_round_derivatives = st.session_state.derivatives_data[f"Round {st.session_state.round}"]
        future_data = current_round_derivatives.get("Future")
        if not future_data:
            st.error("No Future derivative data available for the current round.")
        else:
            company_derivative = st.sidebar.selectbox("Select Company", list(future_data.keys()))
            contracts = st.sidebar.number_input(f"Number of Future contracts for {company_derivative}", min_value=0)
            
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("Buy Derivatives"):
                    buy_derivative(company_derivative, contracts)
            with col2:
                if st.button("Sell Derivatives"):
                    sell_derivative(company_derivative, contracts)
    
    elif selected_security == "Insider":
        if st.session_state.round == 4:
            st.subheader("🕵️ Level 4 Insiders")
            insider_selected = st.selectbox("Select Insider", list(INSIDERS_LEVEL_4.keys()))
            insider_details = INSIDERS_LEVEL_4[insider_selected]

            st.write(f"**Cost ($):** {insider_details['cost']}")

            # Show hint only if purchased
            if insider_selected in st.session_state.insider_purchases.get(f"Round {st.session_state.round}", []):
                st.write(f"**Hint:** {insider_details['hint']}")
            else:
                if st.button("Buy Hint"):
                    buy_insider_hint(insider_selected)
        else:
            st.error("Insider hints are only available in Round 4.")

    
    elif selected_security == "Green Bonds":
        if st.session_state.round == 5:
            st.subheader("🌱 Green Bond Investment (Round 5)")
            st.write("You must invest at least 15% of your starting cash in green bonds.")
            bond_selected = st.selectbox("Select Green Bond", list(GREEN_BONDS.keys()))
            bond_details = GREEN_BONDS[bond_selected]
            st.write(f"**Country:** {bond_details['country']}")
            st.write(f"**Coupon Rate:** {bond_details['coupon_rate']}%")
            st.write(f"**Maturity:** {bond_details['maturity']}")
            st.write(f"**Rating:** {bond_details['rating']}")

            investment_amount = st.number_input("Investment Amount ($)", min_value=0, max_value=int(st.session_state.cash))
            if st.button("Invest in Green Bond"):
                invest_in_green_bond(bond_selected, investment_amount)

            # Enforce the 15% rule at the end of Round 5
            if st.button("Submit Round 5"):
                enforce_green_bond_rule()
                st.session_state.round += 1
                st.rerun()
        elif st.session_state.round in [6, 7]:
            st.subheader("🌱 Green Bond Management")
            if st.session_state.green_bonds:
                for bond, details in st.session_state.green_bonds.items():
                    if details["active"]:
                        st.write(f"**Bond:** {bond}")
                        st.write(f"**Amount Invested:** ${details['amount']:.2f}")
                        if st.button(f"Withdraw {bond}"):
                            withdraw_green_bond(bond)
            else:
                st.write("No active green bond investments.")
        else:
            st.info("Green Bond investments are only available in Round 5.")

    # Calculate and add interest in Rounds 6 and 7
    if st.session_state.round in [6, 7]:
        calculate_green_bond_interest()

    # Display Green Bond Portfolio
    if st.session_state.green_bonds:
        st.subheader("🌱 Green Bond Portfolio")
        green_bond_df = pd.DataFrame([
            {
                "Bond": bond,
                "Amount Invested ($)": details["amount"],
                "Coupon Rate (%)": GREEN_BONDS[bond]["coupon_rate"],
                "Maturity": GREEN_BONDS[bond]["maturity"],
                "Status": "Active" if details["active"] else "Withdrawn"
            }
            for bond, details in st.session_state.green_bonds.items()
        ])
        st.table(green_bond_df)
    else:
        st.subheader("🌱 Green Bond Portfolio")
        st.write("No green bonds purchased yet.")

    # Display Loan Information
    if st.session_state.loan_taken > 0:
        st.subheader("🏦 Loan Information")
        st.write(f"Total Loan Taken: ${st.session_state.loan_taken:.2f}")

    # Main Content Display 
    st.header(f"📊 Round {st.session_state.round}")
    display_orders_and_positions()
    if selected_security == "Shares":
        current_prices = st.session_state.companies[f"Round {st.session_state.round}"]
        all_companies = []
        for country, companies in current_prices.items():
            for company, price in companies.items():
                all_companies.append({"Country": country, "Company": company, "Current Price ($)": price})
        all_companies_df = pd.DataFrame(all_companies)
        st.subheader("📈 Current Stock Prices")
        st.table(all_companies_df)

        if st.session_state.portfolio or st.session_state.short_positions:
            portfolio_data = []
            # Add long positions
            for company, data in st.session_state.portfolio.items():
                current_price = None
                for country, companies in current_prices.items():
                    if company in companies:
                        current_price = companies[company]
                        break
                if current_price is None:
                    current_price = 0
                
                networth = data['shares'] * current_price
                portfolio_data.append([
                    company, 
                    current_price, 
                    data['shares'], 
                    data['total_spent'], 
                    data.get('total_stt', 0),  
                    networth,
                    "Long"
                ])
            
            # Add short positions
            for company, data in st.session_state.short_positions.items():
                current_price = None
                for country, companies in current_prices.items():
                    if company in companies:
                        current_price = companies[company]
                        break
                if current_price is None:
                    current_price = 0
                
                networth = -data['shares'] * current_price  # Negative because it's a short position
                portfolio_data.append([
                    company, 
                    current_price, 
                    -data['shares'],  # Show as negative to indicate short
                    data['short_value'], 
                    0,  # No STT for short positions
                    networth,
                    "Short"
                ])
            
            portfolio_df = pd.DataFrame(
                portfolio_data, 
                columns=["Company", "Current Price ($)", "No. of shares", "Total amount spent", "Total STT Paid", "Networth", "Type"]
            )
            # Format numbers
            for col in ['Current Price ($)', 'Total amount spent', 'Total STT Paid', 'Networth']:
                portfolio_df[col] = portfolio_df[col].apply(lambda x: round(x, 2))

    elif selected_security == "Forex":
        current_round_forex = st.session_state.forex_data[f"Round {st.session_state.round}"]
        forex_rates_df = pd.DataFrame([
            {"Currency": value['currency'], "Exchange Rate ($)": value['exchange_rate']}
            for key, value in current_round_forex.items()
        ])
        st.subheader("💱 Current Forex Rates")
        st.table(forex_rates_df)

        if st.session_state.forex:
            forex_holdings_data = []
            for currency, data in st.session_state.forex.items():
                exchange_rate = current_round_forex[currency]['exchange_rate']
                networth = data['amount'] * exchange_rate
                forex_holdings_data.append([currency, exchange_rate, data['amount'], data['total_spent'], data['total_stt'], networth])
            forex_holdings_df = pd.DataFrame(forex_holdings_data, columns=["Currency", "Exchange Rate ($)", "Amount", "Total amount spent", "Total STT Paid", "Networth"])
            

    elif selected_security == "Derivatives":
    # Get current round derivatives data
        current_round_derivatives = st.session_state.derivatives_data[f"Round {st.session_state.round}"]
        
        # Prepare a list of all futures derivatives
        all_futures = []
        if "Future" in current_round_derivatives:
            for company, details in current_round_derivatives["Future"].items():
                all_futures.append({
                    "Company": company,
                    "Current Price ($)": details['price']
                })
        
        # Create a DataFrame and display it
        if all_futures:
            all_futures_df = pd.DataFrame(all_futures)
            st.subheader("📈 Current Futures Prices")
            st.table(all_futures_df)
        else:
            st.error("No futures data available for the current round.")
            
        if st.session_state.derivatives:
            derivatives_holdings_data = []
            for key, data in st.session_state.derivatives.items():
                try:
                    # Split the ticker into company name and expiry round based on underscores
                    parts = key.split("_")
                    if len(parts) == 3:  # Ensure we have exactly 3 parts: <CompanyName>, Fut, <Expiry>
                        company = parts[0]
                        expiry = parts[2]
                    else:
                        raise ValueError(f"Unexpected ticker format: {key}")
                except ValueError as e:
                    st.error(f"Error parsing ticker: {e}")
                
                # Append derivative holdings data with default values for missing keys
                derivatives_holdings_data.append([
                    company,
                    data.get('contracts', 0),          # Default to 0 if 'contracts' is missing
                    data.get('total_spent', 0),        # Default to 0 if 'total_spent' is missing
                    data.get('total_stt', 0)           # Default to 0 if 'total_stt' is missing
                ])
            
            # Create DataFrame and display it
            derivatives_holdings_df = pd.DataFrame(
                derivatives_holdings_data,
                columns=["Company", "Contracts", "Total amount spent", "Total STT Paid"]
            )
            


    st.sidebar.subheader("⏭️ Round Progression")
    password = st.sidebar.text_input("Enter Password to Proceed to Next Round", type="password")
    confirmation = st.sidebar.checkbox("Confirm.")

    if st.sidebar.button("Submit Round"):
        if not confirmation:
            st.sidebar.error("❌ Please confirm by checking the box above.")
        elif password == ROUND_PASSWORDS[st.session_state.round + 1]:
            if st.session_state.round < 7:
                st.session_state.round += 1
                process_futures_expiry()
                #update_user_metrics(user_id)
                st.rerun()
                # Allocate IPO shares when moving to Round 3
                if st.session_state.round == 6:
                    st.session_state.cash += 250000000
                    st.rerun()
                
            else:
                st.sidebar.error("🎉 All rounds completed! Final cash balance: ${:.2f}".format(st.session_state.cash))
        else:
            st.sidebar.error("❌ Incorrect password!")
