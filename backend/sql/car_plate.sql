CREATE TABLE parking_vehicles (
    plate_number TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('active', 'inactive')),
    valid_until TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1
);

INSERT INTO parking_vehicles
    (plate_number, status, valid_until)
VALUES
    ('12가3456', 'active', NULL),
    ('34나7890', 'inactive', NULL),
    ('56다1111', 'active', '2026-08-01T00:00:00Z');