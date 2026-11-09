USE fooddna;

-- Phase 7-10 additive migration. Review and back up the target database first.
-- Adds optional order assignment/offer references and a server-calculated discount.
-- Run each ALTER only once; on an already-migrated database, duplicate-column or
-- duplicate-FK errors indicate the matching change has already been applied.
ALTER TABLE orders ADD COLUMN delivery_partner_id BIGINT NULL;
ALTER TABLE orders ADD COLUMN offer_id BIGINT NULL;
ALTER TABLE orders ADD COLUMN discount_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00;
ALTER TABLE orders ADD INDEX idx_orders_delivery_partner (delivery_partner_id);
ALTER TABLE orders ADD CONSTRAINT fk_orders_delivery_partner
    FOREIGN KEY (delivery_partner_id) REFERENCES delivery_partners(id);
ALTER TABLE orders ADD CONSTRAINT fk_orders_offer
    FOREIGN KEY (offer_id) REFERENCES offers(id);
