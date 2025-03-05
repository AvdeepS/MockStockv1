
import streamlit as st
import pandas as pd
import random
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
        padding: 20px;
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

        if 'ipo_subscriptions' not in st.session_state:  # IPO subscriptions
            st.session_state.ipo_subscriptions = {}

initialize_session()
    
ROUND_PASSWORDS = {
    2: "password2",
    3: "password3",
    4: "password4",
    5: "password5",
    6: "password6",
    7: "password7",
}

# ---- Login Screen ----
st.title("Bulls v/s Borders")

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
    
    def process_futures_expiry():
        current_round = st.session_state.round
        expired_futures = []

        # Iterate through all derivatives holdings
        for key, data in list(st.session_state.derivatives.items()):
            parts = key.split("_")
            if len(parts) == 3:  # Format: <CompanyName>_Fut_<Expiry>
                company = parts[0]
                expiry_round = int(parts[2][1:])  # Extract round number from "r5", "r6", etc.

                # Check if the future expires in the current round
                if expiry_round == current_round:
                    # Fetch settlement price from derivatives_data
                    round_key = f"Round {current_round}"
                    future_data = st.session_state.derivatives_data.get(round_key, {}).get("Future", {}).get(key)

                    if not future_data or 'price' not in future_data:
                        st.error(f"Price data missing for {key} in Round {current_round}.")
                        continue

                    settlement_price = future_data['price']
                    contract_size = future_data.get('contract_size', 10000)  # Default contract size

                    # Handle short positions
                    if company in st.session_state.short_positions:
                        short_data = st.session_state.short_positions[company]
                        short_contracts = short_data['contracts']
                        total_short_value = short_contracts * settlement_price * contract_size

                        # Deduct cash for covering short position
                        st.session_state.cash -= total_short_value

                        # Remove short position after settlement
                        del st.session_state.short_positions[company]

                        # Record transaction for settlement of short position
                        st.session_state.transactions.append({
                            'round': current_round,
                            'type': 'Settle Short Future',
                            'company': company,
                            'contracts': short_contracts,
                            'settlement_price': settlement_price,
                            'total_value': total_short_value
                        })
                    else:
                        # Handle long positions
                        long_contracts = data['contracts']
                        total_long_value = long_contracts * settlement_price * contract_size 

                        # Add cash for selling long position
                        st.session_state.cash += total_long_value

                        # Remove long position after settlement
                        del st.session_state.derivatives[key]

                        # Record transaction for settlement of long position
                        st.session_state.transactions.append({
                            'round': current_round,
                            'type': 'Settle Long Future',
                            'company': company,
                            'contracts': long_contracts,
                            'settlement_price': settlement_price,
                            'total_value': total_long_value
                        })

                    expired_futures.append(company)

        if expired_futures:
            st.success(f"✅ Futures expired and settled for: {', '.join(expired_futures)}")
        else:
            st.info("No futures expired in this round.")



    
    st.sidebar.subheader("🔄 Round Management")
    if st.session_state.round < 7:
        if st.sidebar.button("Next Round"):
            process_futures_expiry()
            st.session_state.round += 1
            st.rerun()
    else:
        st.sidebar.write("🎉 All rounds completed!")


    # Display current round number
    st.write(f"Current Round: {st.session_state.round}")
    
    # Dummy IPO data for each round
    ipo_data = {
        'Round 1': {
            "IPO 1": {"company": "Company I Pvt Ltd", "issue_price": 200, "subscription_status": "Open", "total_shares": 1000, "shares_subscribed": 0, "listed": False}
        },
        'Round 2': {
            "IPO 1": {"company": "Company J Pvt Ltd", "issue_price": 250, "subscription_status": "Open", "total_shares": 1000, "shares_subscribed": 0, "listed": False}
        },
        'Round 3': {
            "IPO 1": {"company": "Company K Pvt Ltd", "issue_price": 300, "subscription_status": "Open", "total_shares": 1000, "shares_subscribed": 0, "listed": False}
        },
        'Round 4': {
            "IPO 1": {"company": "Company L Pvt Ltd", "issue_price": 350, "subscription_status": "Open", "total_shares": 1000, "shares_subscribed": 0, "listed": False}
        },
        'Round 5': {
            "IPO 1": {"company": "Company M Pvt Ltd", "issue_price": 400, "subscription_status": "Open", "total_shares": 1000, "shares_subscribed": 0, "listed": False}
        }
    }
    
    # Function to calculate STT
    def calculate_stt(transaction_type, transaction_value):
        stt_rates = {
            'equity': 0.001,  # 0.1% for equity shares
            'ipo': 0.001,     # 0.1% for IPO subscription
            'forex': 0.0001,  # 0.01% for Forex trading
            'derivatives': 0.0005  # 0.05% for derivatives
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
            cover_value = shares_to_cover * current_price  # Total cost/value involved in covering shorts

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
            st.session_state.transactions.append({
                'round': st.session_state.round,
                'type': 'Cover Short',
                'company': company,
                'shares': shares_to_cover,
                'price': current_price,
                'total_added': cover_value
            })
            st.rerun()
            # If the user wants to buy more shares beyond covering the short, process as a normal buy order
            remaining_shares = shares - shares_to_cover
            if remaining_shares > 0:
                total_cost = remaining_shares * current_price
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
                st.session_state.transactions.append({
                    'round': st.session_state.round,
                    'type': 'Buy Shares',
                    'company': company,
                    'shares': remaining_shares,
                    'price': current_price,
                    'stt': stt,
                    'country': country,
                    'total_cost': total_cost_with_stt
                })
                st.success(f"✅ Successfully bought {remaining_shares} shares of {company}!")
                st.rerun()

        else:
            # Normal buy flow (if no short position to cover)
            total_cost = shares * current_price
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
            st.session_state.transactions.append({
                'round': st.session_state.round,
                'type': 'Buy Shares',
                'company': company,
                'shares': shares,
                'price': current_price,
                'stt': stt,
                'country': country,
                'total_cost': total_cost_with_stt
            })
            
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
            short_value = short_shares * current_price
            
            st.session_state.short_positions[company]['shares'] += short_shares
            st.session_state.short_positions[company]['short_price'] += short_value
            st.session_state.short_positions[company]['short_value'] += short_value
            
            # Deduct cash immediately
            total_received = short_value
            stt = calculate_stt('equity', total_received)
            total_received_after_stt = total_received - stt
            
            st.session_state.cash -= total_received_after_stt
            
            st.session_state.transactions.append({
                'round': st.session_state.round,
                'type': 'Short Sell',
                'company': company,
                'shares': short_shares,
                'price': current_price,
                'stt': stt,
                'total_received': total_received_after_stt
            })
            st.success(f"✅ Successfully short sold {short_shares} shares of {company}! (STT: ${stt:.2f})")
            st.rerun()
        
        else:
            company_data = st.session_state.portfolio[company]
            if company_data['shares'] < shares:
                st.error(f"You don't own enough shares of {company} to sell!")
                return

            total_received = shares * current_price
            stt = calculate_stt('equity', total_received)
            total_received_after_stt = total_received - stt

            company_data['shares'] -= shares
            company_data['total_spent'] += total_received
            company_data['total_stt'] += stt
            st.session_state.cash += total_received_after_stt

            if company_data['shares'] <= 0:
                del st.session_state.portfolio[company]

            st.session_state.transactions.append({
                'round': st.session_state.round,
                'type': 'Sell Shares',
                'company': company,
                'shares': shares,
                'price': current_price,
                'stt': stt,
                'country': company_data['country'],
                'total_received': total_received_after_stt
            })
            st.success(f"✅ Successfully sold {shares} shares of {company}! (STT: ${stt:.2f})")
            st.rerun()

    # IPO and Forex functions
    def subscribe_to_ipo(ipo_name, shares):
        if shares <= 0:
            st.error("Please enter a valid number of shares to subscribe.")
            return

        current_round = f"Round {st.session_state.round}"
        ipo_details = ipo_data[current_round][ipo_name]
        if ipo_details["subscription_status"] != "Open":
            st.error("IPO subscription is closed.")
            return

        max_shares = min(shares, ipo_details["total_shares"] - ipo_details["shares_subscribed"])
        if max_shares <= 0:
            st.error("IPO is fully subscribed.")
            return

        total_cost = max_shares * ipo_details["issue_price"]
        stt = calculate_stt('ipo', total_cost)
        total_cost_with_stt = total_cost + stt

        if total_cost_with_stt > st.session_state.cash:
            st.error("Not enough cash to subscribe to this IPO!")
            return

        st.session_state.cash -= total_cost_with_stt
        st.session_state.ipo_subscriptions.setdefault(current_round, []).append({
            'ipo_name': ipo_name,
            'shares': max_shares,
            'price': ipo_details["issue_price"],
            'amount': total_cost_with_stt,
            'status': 'Pending'
        })

        st.session_state.transactions.append({
            'round': st.session_state.round,
            'type': 'Subscribe to IPO',
            'ipo_name': ipo_name,
            'shares': max_shares,
            'price': ipo_details["issue_price"],
            'stt': stt,
            'total_cost': total_cost_with_stt
        })
        st.success(f"✅ IPO subscription for {max_shares} shares of {ipo_name} is pending.")
        st.rerun()

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
            cover_value = amount_to_cover * exchange_rate

            # Calculate STT if needed
            stt = calculate_stt('forex', cover_value)
            # Add the cover value back to cash
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
            st.session_state.transactions.append({
                'round': st.session_state.round,
                'type': 'Cover Short Forex',
                'currency': currency,
                'amount': amount_to_cover,
                'exchange_rate': exchange_rate,
                'total_added': cover_value
            })
            st.rerun()
            # If the user wants to buy more forex beyond covering the short, process as a normal buy order
            remaining_amount = amount - amount_to_cover
            if remaining_amount > 0:
                total_cost = remaining_amount * exchange_rate
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
                st.session_state.transactions.append({
                    'round': st.session_state.round,
                    'type': 'Buy Forex',
                    'currency': currency,
                    'amount': remaining_amount,
                    'exchange_rate': exchange_rate,
                    'stt': stt,
                    'total_cost': total_cost_with_stt
                })
                st.success(f"✅ Successfully bought {remaining_amount} {currency}!")
                st.rerun()
        else:
            # Normal buy flow (if no short position to cover)
            total_cost = amount * exchange_rate
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

            st.session_state.transactions.append({
                'round': st.session_state.round,
                'type': 'Buy Forex',
                'currency': currency,
                'amount': amount,
                'exchange_rate': exchange_rate,
                'stt': stt,
                'total_cost': total_cost_with_stt
            })
            st.success(f"✅ Successfully bought {amount} {currency}! (STT: ${stt:.2f})")
            st.rerun()

    def sell_forex(currency, amount):
        if amount <= 0:
            st.error("Please enter a valid amount to sell.")
            return

        # Get current round exchange rate
        current_round_forex = st.session_state.forex_data[f"Round {st.session_state.round}"]
        exchange_rate = current_round_forex[currency]['exchange_rate']

        # If user does not hold this currency, treat as a short sell
        if currency not in st.session_state.forex:
            if currency not in st.session_state.short_positions:
                st.session_state.short_positions[currency] = {
                    'amount': 0,
                    'short_price': 0,
                    'short_value': 0
                }
            short_amount = amount
            short_value = short_amount * exchange_rate

            st.session_state.short_positions[currency]['amount'] += short_amount
            st.session_state.short_positions[currency]['short_price'] += short_value
            st.session_state.short_positions[currency]['short_value'] += short_value

            # For a short sale, cash is reduced (you receive cash, but since you're short you “pay” the obligation)
            total_received = short_value
            stt = calculate_stt('forex', total_received)
            total_received_after_stt = total_received - stt

            st.session_state.cash -= total_received_after_stt

            st.session_state.transactions.append({
                'round': st.session_state.round,
                'type': 'Short Sell Forex',
                'currency': currency,
                'amount': short_amount,
                'exchange_rate': exchange_rate,
                'stt': stt,
                'total_received': total_received_after_stt
            })
            st.success(f"✅ Successfully short sold {short_amount} of {currency}! (STT: ${stt:.2f})")
            st.rerun()
        else:
            # If user holds the currency, ensure they have enough to sell
            if st.session_state.forex[currency]['amount'] < amount:
                st.error("You don't own enough currency to sell!")
                return

            total_received = amount * exchange_rate
            stt = calculate_stt('forex', total_received)
            total_received_after_stt = total_received - stt

            st.session_state.forex[currency]['amount'] -= amount
            st.session_state.forex[currency]['total_spent'] -= total_received
            st.session_state.forex[currency]['total_stt'] += stt
            st.session_state.cash += total_received_after_stt

            if st.session_state.forex[currency]['amount'] <= 0:
                del st.session_state.forex[currency]

            st.session_state.transactions.append({
                'round': st.session_state.round,
                'type': 'Sell Forex',
                'currency': currency,
                'amount': amount,
                'exchange_rate': exchange_rate,
                'stt': stt,
                'total_received': total_received_after_stt
            })
            st.success(f"✅ Successfully sold {amount} {currency}! (STT: ${stt:.2f})")
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
        price = derivative_details['price']
        contract_size = derivative_details['contract_size']

        # --- Cover Short Derivative Position (if exists) ---
        if company in st.session_state.short_positions and st.session_state.short_positions[company].get('contracts', 0) > 0:
            short_data = st.session_state.short_positions[company]

            # Determine how many shorted contracts to cover
            contracts_to_cover = min(contracts, short_data['contracts'])
            cover_value = contracts_to_cover * price * contract_size  # Total value involved in covering shorts

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
            st.session_state.transactions.append({
                'round': st.session_state.round,
                'type': 'Cover Short Derivative',
                'company': company,
                'contracts': contracts_to_cover,
                'price': price,
                'total_added': cover_value
            })

            # Reduce the requested contracts by the number already covered
            contracts -= contracts_to_cover

            # If all contracts were used to cover shorts, refresh UI and exit
            if contracts <= 0:
                st.rerun()

        # --- Normal Buy Flow for Remaining Contracts ---
        total_cost = contracts * price * contract_size * 0.25  # Margin requirement applies here
        stt = calculate_stt('derivatives', total_cost)
        total_cost_with_stt = total_cost + stt

        if total_cost_with_stt > st.session_state.cash:
            st.error("Not enough cash to buy these futures contracts!")
            return

        # Update derivatives holdings
        if company not in st.session_state.derivatives:
            st.session_state.derivatives[company] = {'contracts': 0, 'total_spent': 0, 'margin_required': 0, 'price': price}

        st.session_state.derivatives[company]['contracts'] += contracts
        st.session_state.derivatives[company]['total_spent'] += total_cost
        st.session_state.derivatives[company]['margin_required'] += total_cost

        # Deduct cash and record transaction
        st.session_state.cash -= total_cost_with_stt
        st.session_state.transactions.append({
            'round': st.session_state.round,
            'type': 'Buy Derivative',
            'derivative_type': "Future",
            'company': company,
            'contracts': contracts,
            'price': price,
            'stt': stt,
            'total_cost': total_cost_with_stt
        })

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
        price = derivative_details['price']
        contract_size = derivative_details['contract_size']

        # Calculate total value for the sale with margin (25%)
        total_value = contracts * price * contract_size * 0.25

        # --- Short Sell Flow ---
        if company not in st.session_state.derivatives or st.session_state.derivatives[company]['contracts'] < contracts:
            
            # Treat as a short sell if not enough long positions exist
            if company not in st.session_state.short_positions:
                st.session_state.short_positions[company] = {'contracts': 0, 'short_value': 0}

            short_value = contracts * price * contract_size * 0.25  # Only receive margin equivalent for shorts
            st.session_state.short_positions[company]['contracts'] += contracts
            st.session_state.short_positions[company]['short_value'] += short_value

            # Deduct cash for short liability
            st.session_state.cash -= short_value

            # Record short sell transaction
            st.session_state.transactions.append({
                'round': st.session_state.round,
                'type': 'Short Sell Derivative',
                'derivative_type': "Future",
                'company': company,
                'contracts': contracts,
                'price': price,
                'total_received': short_value
            })
            st.rerun()
            st.success(f"✅ Successfully short sold {contracts} Future contracts for {company}!")
        
        else:
            # --- Normal Selling Flow ---
            if company not in st.session_state.derivatives or st.session_state.derivatives[company]['contracts'] < contracts:
                st.error(f"You don't own enough Future contracts for {company} to sell!")
                return

            # Update derivatives holdings
            st.session_state.derivatives[company]['contracts'] -= contracts
            if st.session_state.derivatives[company]['contracts'] == 0:
                del st.session_state.derivatives[company]

            # Add cash and record transaction
            total_received_after_margin = total_value
            st.session_state.cash += total_received_after_margin
            st.session_state.transactions.append({
                'round': st.session_state.round,
                'type': 'Sell Derivative',
                'derivative_type': "Future",
                'company': company,
                'contracts': contracts,
                'price': price,
                'total_received': total_received_after_margin
            })

            st.success(f"✅ Successfully sold {contracts} Future contracts for {company}!")

        # Re-run UI after transactions
        st.rerun()

    # Helper functions
    def check_negative_cash():
        if st.session_state.cash < 0:
            st.session_state.cash = 0
            st.error("💸 You have run out of cash and can no longer play. Please restart the game.")
            return True
        return False

    def process_ipo_results():
        current_round = f"Round {st.session_state.round}"
        if current_round in st.session_state.ipo_subscriptions:
            for subscription in st.session_state.ipo_subscriptions[current_round]:
                if subscription["status"] == "Pending":
                    if random.random() < 0.5:
                        subscription["status"] = "Allocated"
                        company_name = ipo_data[current_round][subscription["ipo_name"]]["company"]
                        if company_name not in st.session_state.portfolio:
                            st.session_state.portfolio[company_name] = {
                                "shares": 0,
                                "total_spent": 0,
                                "total_stt": 0,
                                "country": "India"
                            }
                        st.session_state.portfolio[company_name]["shares"] += subscription["shares"]
                        st.session_state.portfolio[company_name]["total_spent"] += subscription["amount"]
                        st.session_state.portfolio[company_name]["total_stt"] += calculate_stt('ipo', subscription["amount"])
                    else:
                        subscription["status"] = "Not Allocated"
                        st.session_state.cash += subscription["amount"]



    # Streamlit app layout
    st.title("📈 Trading Platform")
    st.sidebar.write(f"💰 Cash in Hand ($): {st.session_state.cash:.2f}")

    # Security Type Selection
    st.sidebar.subheader("📈 Trade Securities")
    selected_security = st.sidebar.selectbox(
        "Select security type to trade",
        ["Shares", "IPO", "Forex", "Derivatives"]
    )

    # Shares Trading Section
    if selected_security == "Shares":
        current_prices = st.session_state.companies[f"Round {st.session_state.round}"]
        all_companies = {}
        for country, companies in current_prices.items():
            all_companies[country] = list(companies.keys())
        
        current_round_ipo = ipo_data.get(f"Round {st.session_state.round}", {})
        for ipo_name, ipo_details in current_round_ipo.items():
            if ipo_details["listed"]:
                company_name = ipo_details["company"]
                if "India" not in all_companies:
                    all_companies["India"] = []
                if company_name not in all_companies["India"]:
                    all_companies["India"].append(company_name)
        
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

    # IPO Trading Section
    elif selected_security == "IPO":
        current_round_ipo = ipo_data.get(f"Round {st.session_state.round}", {})
        ipo_selected = st.sidebar.selectbox("Select IPO", list(current_round_ipo.keys()))
        ipo_details = current_round_ipo.get(ipo_selected, {})
        
        st.sidebar.write(f"**Company:** {ipo_details.get('company', '')}")
        st.sidebar.write(f"**Issue Price:** ${ipo_details.get('issue_price', '')}")
        st.sidebar.write(f"**Status:** {ipo_details.get('subscription_status', 'Closed')}")
        
        ipo_shares = st.sidebar.number_input(f"Number of shares for {ipo_selected}", min_value=0)
        
        if st.sidebar.button("Subscribe to IPO"):
            subscribe_to_ipo(ipo_selected, ipo_shares)

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


    # Main Content Display
    st.header(f"📊 Round {st.session_state.round}")

    if selected_security == "Shares":
        current_prices = st.session_state.companies[f"Round {st.session_state.round}"]
        all_companies = []
        for country, companies in current_prices.items():
            for company, price in companies.items():
                all_companies.append({"Country": country, "Company": company, "Current Price ($)": price})
        all_companies_df = pd.DataFrame(all_companies)
        st.subheader("📈 Current Stock Prices (All Countries)")
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
            st.subheader("💼 Your Portfolio")
            st.table(portfolio_df)
        else:
            st.subheader("💼 Your Portfolio")
            st.write("No shares owned or shorted in the current round.")

    elif selected_security == "IPO":
        current_round_ipo = ipo_data.get(f"Round {st.session_state.round}", {})
        ipo_list = []
        for ipo_name, ipo_details in current_round_ipo.items():
            ipo_list.append({
                "IPO Name": ipo_name,
                "Company": ipo_details['company'],
                "Issue Price ($)": ipo_details['issue_price'],
                "Status": ipo_details['subscription_status']
            })
        ipo_df = pd.DataFrame(ipo_list)
        st.subheader("📈 Current IPO Listings")
        st.table(ipo_df)

    elif selected_security == "Forex":
        current_round_forex = st.session_state.forex_data[f"Round {st.session_state.round}"]
        forex_rates_df = pd.DataFrame([
            {"Currency": key, "Currency Name": value['currency'], "Exchange Rate ($)": value['exchange_rate']}
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
            st.subheader("💱 Your Forex Holdings")
            st.table(forex_holdings_df)
        else:
            st.subheader("💱 Your Forex Holdings")
            st.write("No Forex holdings in the current round.")

    elif selected_security == "Derivatives":
    # Get current round derivatives data
        current_round_derivatives = st.session_state.derivatives_data[f"Round {st.session_state.round}"]
        
        # Prepare a list of all futures derivatives
        all_futures = []
        if "Future" in current_round_derivatives:
            for company, details in current_round_derivatives["Future"].items():
                all_futures.append({
                    "Country": details.get('country', 'N/A'),  # Add country information
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
            st.subheader("📜 Your Derivatives Holdings")
            st.table(derivatives_holdings_df)
        else:
            st.subheader("📜 Your Derivatives Holdings")
            st.write("No derivatives holdings in the current round.")


    # Transaction Summary
    st.subheader("📝 Transaction Summary")
    if st.session_state.transactions:
        transactions_df = pd.DataFrame(st.session_state.transactions)
        transactions_df = transactions_df.fillna({
            'ompany': '',
            'shares': 0,
            'price': 0,
            'country': '',
            'currency': '',
            'amount': 0,
            'exchange_rate': 0,
            'ipo_name': '',
            'derivative_type': '',
            'contracts': 0
        })
        st.table(transactions_df)
    else:
        st.write("No transactions recorded yet.")

    # Final cash check
    if check_negative_cash():
        st.error("💸 You have run out of cash and can no longer play. Please restart the game.")
