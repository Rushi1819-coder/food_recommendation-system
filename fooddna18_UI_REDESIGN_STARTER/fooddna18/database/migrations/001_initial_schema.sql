USE fooddna;

INSERT INTO roles (name, description)
VALUES
    ('customer', 'Normal Food DNA customer'),
    ('restaurant_admin', 'Restaurant administrator'),
    ('staff', 'Chef or restaurant staff member'),
    ('delivery_partner', 'Delivery partner'),
    ('super_admin', 'System administrator')
ON DUPLICATE KEY UPDATE
    description = VALUES(description);