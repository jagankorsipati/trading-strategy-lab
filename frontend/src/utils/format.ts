export const percent = (value: unknown) => typeof value === 'number' ? new Intl.NumberFormat('en-US', { style: 'percent', maximumFractionDigits: 2 }).format(value) : 'Unavailable'
export const money = (value: unknown) => typeof value === 'number' ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value) : 'Unavailable'
export const number = (value: unknown, digits = 2) => typeof value === 'number' ? value.toFixed(digits) : 'Unavailable'
export const asNumber = (value: unknown) => value === '' || value == null ? null : Number(value)
