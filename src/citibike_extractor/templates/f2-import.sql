insert into tripdata by name (
    select ride_id, rideable_type, started_at, ended_at,
           case when ended_at > started_at then ended_at - started_at else null end trip_duration,
           start_station_name, start_station_id,
           ST_MakePoint(start_lng, start_lat) start_station_location,
           end_station_name, end_station_id,
           ST_MakePoint(end_lng, end_lat) end_station_location,
           member_casual, NULL bike_id, NULL birth_year, NULL gender
    from input_table);