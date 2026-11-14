-- Seed data for the IS2108 coffee subscription application.
--
-- Run this file from the IS2108proj directory with:
--   sqlite3 db.sqlite3 < sql/seed_data.sql
--
-- This script clears CORE application data and recreates it. It deliberately
-- keeps auth_user rows so an existing admin account is not deleted. The five
-- seed customer accounts are created with an unusable password ('!').
-- If you want a completely empty database first, run `python3 manage.py flush`
-- and create an admin with `python3 manage.py createsuperuser` before running
-- this file.

PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- Delete child rows before parent rows.
DELETE FROM core_cartitem;
DELETE FROM core_cart;
DELETE FROM core_questionnaireresponse;
DELETE FROM core_review;
DELETE FROM core_orderitem;
DELETE FROM core_order;
DELETE FROM core_customersubscription;
DELETE FROM core_bundleitem;
DELETE FROM core_subscriptionbundle;
DELETE FROM core_product;
DELETE FROM core_category;
DELETE FROM core_customerprofile;

-- Keep the SQLite row ids predictable for the application tables.
DELETE FROM sqlite_sequence
WHERE name IN (
    'core_cartitem', 'core_cart', 'core_questionnaireresponse',
    'core_review', 'core_orderitem', 'core_order',
    'core_customersubscription', 'core_bundleitem',
    'core_subscriptionbundle', 'core_product', 'core_category',
    'core_customerprofile'
);

INSERT INTO core_category (id, name, description) VALUES
    (1, 'whole_bean', 'Whole coffee beans for grinding at home.'),
    (2, 'ground', 'Freshly ground coffee for common brewing methods.'),
    (3, 'instant', 'Quick and convenient instant coffee.'),
    (4, 'drip_bag', 'Single-serve drip bags for easy brewing.');

INSERT INTO core_product (
    id, name, description, price, tasting_notes, caffeine_type,
    roast_level, origin_country, stock_level, reorder_threshold,
    is_visible, image, created_at, category_id
) VALUES
    (1, 'Ethiopia Yirgacheffe',
        'Bright single-origin beans with a floral finish.', 18.50,
        'Jasmine, citrus, honey', 'caffeinated', 'light', 'Ethiopia',
        7, 10, 1, 'product_images/ethiopian-yirgacheffe-coffee-pumphreys-.jpg', '2026-01-08 09:00:00', 1),
    (2, 'Colombia Supremo',
        'Balanced beans with a smooth everyday profile.', 16.00,
        'Caramel, red apple, cocoa', 'caffeinated', 'medium', 'Colombia',
        42, 12, 1, NULL, '2026-01-09 09:00:00', 1),
    (3, 'Sumatra Mandheling',
        'Full-bodied beans with a rich earthy character.', 19.50,
        'Dark chocolate, cedar, spice', 'caffeinated', 'dark', 'Indonesia',
        4, 8, 1, NULL, '2026-01-10 09:00:00', 1),
    (4, 'House Blend Ground',
        'A dependable medium roast for daily brewing.', 14.00,
        'Toffee, nuts, milk chocolate', 'caffeinated', 'medium', 'Brazil',
        25, 10, 1, NULL, '2026-01-11 09:00:00', 2),
    (5, 'French Roast Ground',
        'A bold dark roast with a smoky finish.', 15.50,
        'Smoke, bittersweet chocolate, molasses', 'caffeinated', 'dark', 'Vietnam',
        0, 8, 1, NULL, '2026-01-12 09:00:00', 2),
    (6, 'Colombian Instant',
        'Smooth instant coffee for a quick cup.', 12.00,
        'Cocoa, brown sugar', 'caffeinated', 'medium', 'Colombia',
        60, 15, 1, NULL, '2026-01-13 09:00:00', 3),
    (7, 'Midnight Decaf',
        'A rich decaffeinated blend for evening coffee.', 17.00,
        'Roasted almond, cocoa, caramel', 'decaf', 'dark', 'Mexico',
        9, 10, 1, NULL, '2026-01-14 09:00:00', 2),
    (8, 'Floral Drip Bags',
        'Light roast drip bags with a clean finish.', 13.50,
        'Jasmine, peach, bergamot', 'caffeinated', 'light', 'Ethiopia',
        30, 8, 1, NULL, '2026-01-15 09:00:00', 4),
    (9, 'Chocolate Drip Bags',
        'Convenient drip bags with a comforting chocolate profile.', 14.50,
        'Chocolate, hazelnut, raisin', 'caffeinated', 'medium', 'Brazil',
        6, 10, 1, NULL, '2026-01-16 09:00:00', 4),
    (10, 'Espresso Roast',
        'A concentrated roast designed for espresso machines.', 21.00,
        'Dark chocolate, cherry, toasted sugar', 'caffeinated', 'dark', 'Brazil',
        18, 8, 1, NULL, '2026-01-17 09:00:00', 1);

INSERT INTO core_subscriptionbundle (
    id, name, description, price_per_delivery, billing_frequency, is_active
) VALUES
    (1, 'Daily Brew Starter',
        'A flexible monthly selection for everyday coffee drinkers.', 32.50, 'monthly', 1),
    (2, 'Espresso Explorer',
        'A monthly bundle featuring bold espresso-friendly coffees.', 45.00, 'monthly', 1),
    (3, 'Decaf Discovery',
        'A yearly decaf-focused bundle for relaxed evening brewing.', 79.90, 'yearly', 1);

INSERT INTO core_bundleitem (id, quantity, product_id, subscription_bundle_id) VALUES
    (1, 1, 1, 1),
    (2, 1, 4, 1),
    (3, 1, 2, 1),
    (4, 1, 10, 2),
    (5, 1, 3, 2),
    (6, 1, 4, 2),
    (7, 1, 7, 3),
    (8, 1, 9, 3);

-- Seed customer users without overwriting an existing account with the same
-- username. Password '!' is Django's unusable-password marker.
INSERT OR IGNORE INTO auth_user (
    password, last_login, is_superuser, username, last_name, email,
    is_staff, is_active, date_joined, first_name
) VALUES
    ('!', NULL, 0, 'seed_alice', 'Tan', 'alice@example.com', 0, 1, '2026-01-20 09:00:00', 'Alice'),
    ('!', NULL, 0, 'seed_ben', 'Lim', 'ben@example.com', 0, 1, '2026-01-21 09:00:00', 'Ben'),
    ('!', NULL, 0, 'seed_carol', 'Lee', 'carol@example.com', 0, 1, '2026-01-22 09:00:00', 'Carol'),
    ('!', NULL, 0, 'seed_dylan', 'Wong', 'dylan@example.com', 0, 1, '2026-01-23 09:00:00', 'Dylan'),
    ('!', NULL, 0, 'seed_emma', 'Ng', 'emma@example.com', 0, 1, '2026-01-24 09:00:00', 'Emma');

INSERT INTO core_customerprofile (
    id, phone_number, created_at, user_id, delivery_address
) VALUES
    (1, '+65 9000 1001', '2026-01-20 09:05:00',
        (SELECT id FROM auth_user WHERE username = 'seed_alice'),
        '10 Orchard Road, Singapore 238823'),
    (2, '+65 9000 1002', '2026-01-21 09:05:00',
        (SELECT id FROM auth_user WHERE username = 'seed_ben'),
        '20 Tiong Bahru Road, Singapore 168732'),
    (3, '+65 9000 1003', '2026-01-22 09:05:00',
        (SELECT id FROM auth_user WHERE username = 'seed_carol'),
        '30 Tampines Street 21, Singapore 529392'),
    (4, '+65 9000 1004', '2026-01-23 09:05:00',
        (SELECT id FROM auth_user WHERE username = 'seed_dylan'),
        '40 Bukit Timah Road, Singapore 259835'),
    (5, '+65 9000 1005', '2026-01-24 09:05:00',
        (SELECT id FROM auth_user WHERE username = 'seed_emma'),
        '50 East Coast Road, Singapore 428769');

INSERT INTO core_customersubscription (
    id, start_date, next_delivery_date, bundle_id, customer_id, status
) VALUES
    (1, '2026-02-01 09:00:00', '2026-11-20', 1, 1, 'active'),
    (2, '2026-02-05 09:00:00', '2026-11-25', 1, 2, 'active'),
    (3, '2026-02-12 09:00:00', '2026-11-18', 2, 3, 'active'),
    (4, '2026-03-01 09:00:00', '2026-11-28', 2, 4, 'active'),
    (5, '2026-03-15 09:00:00', '2026-11-30', 2, 5, 'active'),
    (6, '2026-04-01 09:00:00', NULL, 3, 1, 'cancelled'),
    (7, '2026-05-10 09:00:00', '2026-12-10', 1, 3, 'active'),
    (8, '2026-01-15 09:00:00', NULL, 1, 4, 'cancelled');

-- Historical orders provide enough variation for sales and bundle analytics.
INSERT INTO core_order (
    id, order_type, total_amount, delivery_address, delivery_status,
    created_at, delivery_fee, grand_total, customer_id, subscription_id
) VALUES
    (1, 'one-time', 37.00, '10 Orchard Road, Singapore 238823', 'delivered', '2026-02-03 10:00:00', 5.00, 42.00, 1, NULL),
    (2, 'one-time', 16.00, '20 Tiong Bahru Road, Singapore 168732', 'delivered', '2026-02-18 11:00:00', 5.00, 21.00, 2, NULL),
    (3, 'subscription', 35.00, '30 Tampines Street 21, Singapore 529392', 'delivered', '2026-03-12 09:30:00', 0.00, 35.00, 3, 3),
    (4, 'one-time', 18.50, '40 Bukit Timah Road, Singapore 259835', 'delivered', '2026-03-25 13:00:00', 5.00, 23.50, 4, NULL),
    (5, 'subscription', 42.00, '50 East Coast Road, Singapore 428769', 'delivered', '2026-04-08 09:15:00', 0.00, 42.00, 5, 5),
    (6, 'subscription', 32.00, '10 Orchard Road, Singapore 238823', 'delivered', '2026-04-20 09:00:00', 0.00, 32.00, 1, 1),
    (7, 'one-time', 55.50, '20 Tiong Bahru Road, Singapore 168732', 'delivered', '2026-05-05 14:00:00', 0.00, 55.50, 2, NULL),
    (8, 'one-time', 28.00, '30 Tampines Street 21, Singapore 529392', 'delivered', '2026-05-19 15:00:00', 0.00, 28.00, 3, NULL),
    (9, 'subscription', 40.50, '40 Bukit Timah Road, Singapore 259835', 'delivered', '2026-06-02 09:00:00', 0.00, 40.50, 4, 4),
    (10, 'one-time', 17.00, '50 East Coast Road, Singapore 428769', 'delivered', '2026-06-21 12:00:00', 5.00, 22.00, 5, NULL),
    (11, 'one-time', 27.00, '10 Orchard Road, Singapore 238823', 'delivered', '2026-07-04 10:30:00', 0.00, 27.00, 1, NULL),
    (12, 'subscription', 32.50, '20 Tiong Bahru Road, Singapore 168732', 'delivered', '2026-07-18 09:00:00', 0.00, 32.50, 2, 2),
    (13, 'subscription', 30.00, '30 Tampines Street 21, Singapore 529392', 'delivered', '2026-08-06 09:00:00', 0.00, 30.00, 3, 7),
    (14, 'one-time', 15.50, '40 Bukit Timah Road, Singapore 259835', 'shipped', '2026-08-28 16:00:00', 5.00, 20.50, 4, NULL),
    (15, 'subscription', 40.50, '50 East Coast Road, Singapore 428769', 'roasting', '2026-09-12 09:00:00', 0.00, 40.50, 5, 5),
    (16, 'one-time', 32.00, '10 Orchard Road, Singapore 238823', 'delivered', '2026-09-30 11:00:00', 0.00, 32.00, 1, NULL),
    (17, 'one-time', 43.50, '20 Tiong Bahru Road, Singapore 168732', 'pending', '2026-10-18 14:30:00', 0.00, 43.50, 2, NULL),
    (18, 'one-time', 18.50, '30 Tampines Street 21, Singapore 529392', 'pending', '2026-11-05 10:00:00', 5.00, 23.50, 3, NULL);

INSERT INTO core_orderitem (id, quantity, price_at_purchase, order_id, product_id) VALUES
    (1, 2, 18.50, 1, 1),
    (2, 1, 16.00, 2, 2),
    (3, 1, 21.00, 3, 10),
    (4, 1, 14.00, 3, 4),
    (5, 1, 18.50, 4, 1),
    (6, 2, 21.00, 5, 10),
    (7, 2, 16.00, 6, 2),
    (8, 3, 18.50, 7, 1),
    (9, 2, 14.00, 8, 4),
    (10, 1, 21.00, 9, 10),
    (11, 1, 19.50, 9, 3),
    (12, 1, 17.00, 10, 7),
    (13, 2, 13.50, 11, 8),
    (14, 1, 18.50, 12, 1),
    (15, 1, 14.00, 12, 4),
    (16, 1, 16.00, 13, 2),
    (17, 1, 14.00, 13, 4),
    (18, 1, 15.50, 14, 5),
    (19, 1, 21.00, 15, 10),
    (20, 1, 19.50, 15, 3),
    (21, 2, 16.00, 16, 2),
    (22, 3, 14.50, 17, 9),
    (23, 1, 18.50, 18, 1);

INSERT INTO core_questionnaireresponse (
    id, preferred_roast, predicted_roast, preferred_flavour,
    preferred_brewing_method, preferred_caffeine_type, created_at,
    customer_id, preferred_category_id
) VALUES
    (1, 'light', '', 'floral', 'pour_over', 'caffeinated', '2026-02-02 10:00:00',
        (SELECT id FROM auth_user WHERE username = 'seed_alice'), 1),
    (2, 'medium', '', 'nutty', 'filter', 'caffeinated', '2026-02-17 10:00:00',
        (SELECT id FROM auth_user WHERE username = 'seed_ben'), 2),
    (3, 'dark', '', 'chocolatey', 'espresso', 'caffeinated', '2026-03-11 10:00:00',
        (SELECT id FROM auth_user WHERE username = 'seed_carol'), 1),
    (4, 'dark', '', 'chocolatey', 'french_press', 'decaf', '2026-04-07 10:00:00',
        (SELECT id FROM auth_user WHERE username = 'seed_dylan'), 2),
    (5, 'medium', '', 'fruity', 'filter', 'caffeinated', '2026-05-18 10:00:00',
        (SELECT id FROM auth_user WHERE username = 'seed_emma'), 4);

INSERT INTO core_review (
    id, rating, comment, created_at, customer_id, product_id, is_visible
) VALUES
    (1, 5, 'Bright and fragrant. I would order this again.', '2026-02-10 12:00:00', 1, 1, 1),
    (2, 4, 'Smooth coffee for weekday mornings.', '2026-03-01 12:00:00', 2, 2, 1),
    (3, 5, 'Excellent espresso crema and a rich finish.', '2026-03-20 12:00:00', 3, 10, 1),
    (4, 3, 'Good flavour, but slightly too dark for me.', '2026-04-12 12:00:00', 4, 3, 1),
    (5, 5, 'Very convenient and surprisingly fresh.', '2026-05-24 12:00:00', 5, 8, 1),
    (6, 4, 'Comforting chocolate notes.', '2026-06-25 12:00:00', 1, 7, 1),
    (7, 5, 'My favourite everyday blend.', '2026-08-10 12:00:00', 2, 4, 1),
    (8, 4, 'Great value in the subscription bundle.', '2026-09-18 12:00:00', 2, 10, 1);

INSERT INTO core_cart (id, created_at, updated_at, customer_id) VALUES
    (1, '2026-11-01 09:00:00', '2026-11-05 10:00:00',
        (SELECT id FROM auth_user WHERE username = 'seed_alice')),
    (2, '2026-11-02 09:00:00', '2026-11-06 11:00:00',
        (SELECT id FROM auth_user WHERE username = 'seed_emma'));

INSERT INTO core_cartitem (id, quantity, cart_id, product_id) VALUES
    (1, 1, 1, 3),
    (2, 2, 2, 9);

COMMIT;
