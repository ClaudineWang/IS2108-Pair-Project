# IS2108-Pair-Project

Group number 13

| Full Name | Student Number | Email | Contact Number |
|---|---|---|---|
| Claudine Wang Yan Ning | A0321840N | e1524747@u.nus.edu | 97289882 |
| Sakshi Vashist (Group Leader) | A0321888R | e1524795@u.nus.edu | 96407200 |

## How to Run

From the project root, run:

```bash
cd IS2108proj
python3 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
python manage.py migrate
python manage.py runserver
```

Open the application at [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

### Load the sample SQLite data

After running the migrations, stop the development server and run the following commands from the project root:

```bash
cd IS2108proj
cp -n db.sqlite3 db.sqlite3.before-seed
sqlite3 db.sqlite3 < sql/seed_data.sql
```

The SQL file loads the sample products, subscription bundles, orders, subscriptions, and demo accounts. It also creates the demo logins listed below. The seed script clears and recreates application data, so only run it when you do not need to preserve existing products, orders, carts, subscriptions, or customer profiles.

To create orders for subscription deliveries whose scheduled date has arrived, run this command daily using a scheduler such as cron or Windows Task Scheduler:

```bash
python manage.py process_due_subscriptions
```

For testing, a specific processing date can be supplied:

```bash
python manage.py process_due_subscriptions --date 2026-11-20
```


## Instructions

### Customer

New customers can sign up for an account to access the customer side of the web application.

A demo customer account is also available:

- **Username:** `customer1`
- **Password:** `Customer12345`

### Admin

Log in with the following credentials to access the admin side:

- **Username:** `admin1`
- **Password:** `Admin12345`

The admin credentials can also be used on the customer login page to view the customer page from an administrator’s perspective.

## Demo Video

[YouTube demo video](https://youtu.be/eRTf8XICAcQ)
