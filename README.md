# IS2108-Pair-Project

Group number 13

| Full Name | Student Number | Email | Contact Number |
|---|---|---|---|
| Claudine Wang Yan Ning | A0321840N | e1524747@u.nus.edu | 97289882 |
| Sakshi Vashist | A0321888R | e1524795@u.nus.edu | 96407200 |

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
