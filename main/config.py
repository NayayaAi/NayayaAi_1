# Application-wide constants: districts, police stations, legal acts, folder paths

INDIAN_DISTRICTS = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi", "Puducherry", "Chandigarh"
]

SAMPLE_POLICE_STATIONS = {
    "Delhi": ["North Delhi PS", "South Delhi PS", "East Delhi PS", "West Delhi PS", "Central Delhi PS"],
    "Maharashtra": ["Mumbai North PS", "Mumbai South PS", "Pune PS", "Nagpur PS"],
    "Karnataka": ["Bangalore PS", "Mysore PS", "Hubli PS"],
    "Tamil Nadu": ["Chennai PS", "Coimbatore PS", "Madurai PS"],
    "Uttar Pradesh": ["Lucknow PS", "Kanpur PS", "Varanasi PS"]
}

LEGAL_ACTS = ["IPC", "CRPC", "NIA", "IEA", "HMA", "CPC", "IDA", "MVA"]

PDF_FOLDER = "generated_firs"
UPLOAD_FOLDER = "static/uploads/evidence"
