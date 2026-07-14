insert into tripdata by name (
    select try_strptime(start_time, [
               '%Y-%m-%d %H:%M:%S',
               '%Y-%m-%d %H:%M:%S.%f',
               '%m/%d/%Y %H:%M:%S',
               '%m/%d/%Y %H:%M'
           ]) started_at,
           try_strptime(stop_time, [
               '%Y-%m-%d %H:%M:%S',
               '%Y-%m-%d %H:%M:%S.%f',
               '%m/%d/%Y %H:%M:%S',
               '%m/%d/%Y %H:%M'
           ]) ended_at,
           trip_duration,
           start_station_id,
           start_station_name,
           ST_MakePoint(start_station_longitude, start_station_latitude) start_station_location,
           end_station_id,
           end_station_name,
           ST_MakePoint(end_station_longitude, end_station_latitude) end_station_location,
           bike_id,
           case user_type when 'Subscriber' then 'member' when 'Customer' then 'casual' else NULL end member_casual,
           birth_year,
           nullif(gender, 0) gender,
           case when started_at < '2018-08-20' then 'classic_bike' else null end rideable_type,
           upper(to_hex(hash(rideable_type, started_at, ended_at, trip_duration, start_station_id, start_station_name, start_station_location, end_station_location, member_casual))) ride_id
    from input_table);