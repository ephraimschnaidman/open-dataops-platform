select
    trim(customer_id) as customer_id,
    lower(trim(email)) as email,
    trim(first_name) as first_name,
    trim(last_name) as last_name,
    created_at::timestamptz as created_at,
    upper(trim(country)) as country,
    case lower(trim(region))
        when 'california' then 'CA'
        when 'ca' then 'CA'
        when 'ny' then 'NY'
        when 'texas' then 'TX'
        when 'wa' then 'WA'
        when 'ontario' then 'ON'
        when 'england' then 'ENG'
        when 'british columbia' then 'BC'
        when 'new south wales' then 'NSW'
        else upper(trim(region))
    end as region,
    marketing_opt_in::boolean as marketing_opt_in
from {{ source('ecommerce_raw', 'customers') }}
