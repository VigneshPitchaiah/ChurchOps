-- Add status column to the attendance table
ALTER TABLE church.attendance 
ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'present';

-- Update existing records to set a status
UPDATE church.attendance 
SET status = 'present' 
WHERE check_in_time IS NOT NULL;

-- Set check_in_time to nullable
ALTER TABLE church.attendance 
ALTER COLUMN check_in_time DROP NOT NULL;
