# green_charging_emobility
Open Energy Data Hackdays 2021

[Link to challenge on Hackdays](https://hack.opendata.ch/project/768). Please join this challenge!

## Meter data format

* 'id': Unclear, not used.
* 'Chargepoint': The unique identifier (number or UUID) of the physical charging station. One station can have more than one cable, and hence more than one charging session.
* 'connector': The unique identifier (number or UUID) of the physical cable or attached device. In some cases, a cable can be left in the charging station for a long period of time, and used for multiple charging stations.
* 'charge_log_id': The unique identifier (number or UUID) of a particular session charging a battery
* 'metervalue': Not used
* 'increment': The amount of energy transferred (in watt-hours) in the last 15 minutes (i.e. up to the 'timestamp' value)
* 'timestamp': The time of measurement in UTC.

## CO2 data format

## Coding standards

Please store notebooks in the `Notebooks` directory.

Please store data in the `Data` directory. It will be ignored by git. The data files should be named:

* CH 2020-2021.csv
* metervalues_pseudonymized_2_neu.csv
* metervalues_pseudonymized_1_neu.csv
