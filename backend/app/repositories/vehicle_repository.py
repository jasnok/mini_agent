from app.core.database import connect


class VehicleRepository:
    def find_by_plate(self, plate_number: str) -> dict | None:
        query = """
            SELECT plate_number, status, valid_until, version
            FROM parking_vehicles
            WHERE plate_number = %s
            LIMIT 1
        """

        with connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (plate_number,))
                return cursor.fetchone()


vehicle_repository = VehicleRepository()