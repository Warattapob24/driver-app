import os

# 1. สร้างโฟลเดอร์ .streamlit ถ้ายังไม่มี
if not os.path.exists(".streamlit"):
    os.makedirs(".streamlit")
    print("✅ สร้างโฟลเดอร์ .streamlit เรียบร้อย")

# 2. ข้อมูล Secrets ของคุณ (ผมเอามาประกอบให้ถูกต้องแล้ว)
secrets_content = """
[connections.gsheets]
spreadsheet = "https://docs.google.com/spreadsheets/d/1aXx0K8LB96sQ3yL2LeenlzrhLl7UJrGyjfi8QFS3G1o/edit?usp=sharing"

[connections.gsheets.service_account]
project_id = "drivers-481801"
private_key_id = "6150a7dd212b141acb92a31be5b3eeff4684d0fc"
private_key = "-----BEGIN PRIVATE KEY-----\\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC1agIYg2P4L0sA\\nCsMYzctk+/10YcInZ29fI/EjyTj3oM2WeswV8NqcUvdYt3TY9w4p2QmxMkqFjqyF\\nRDQworH/3V+RHdijLyZY/NhSosgWE+hMvwYd/3rGSxVannFfTLN+QE490NXp659B\\nyc7B5AlrI/COVDfpfl9rYMYb8GlxAZ+QjSgU9HBASDWPWdUFyl0T5eJh0fRie6+d\\n5Y9KDIZ9Bj+Yzfoo3wVb9rJpO5haBnah+EALNebqTvJvBdlvLbGiKx3OWfKDgYTV\\nKyz7k5YG5v01duCAQhhX/G2qnavRLr1wjA4y2ItHfb9kzAPiBkGiu/lAQV6fTsSS\\nIm9+aO7rAgMBAAECggEAEGZTZyzliieYU5oldeYQt4HSMUWvHAnNNyAUKgSESlp2\\ni15xeaBK2uvjIVmATibTWHQe3K5rrzQtI2T9hNIIXlWAUKmOjn3yLQQ6eAnwJZLK\\nIrn4Dxkr26Yo+YauQAu6hDTC/fKVi+55eKSKNNvtAAsBMZSqc0ixzo6yig8LMSRp\\n9ilVUOlQIywDtY0Vtx2XshSmxC75Vei7XpvjRQN3ZX+xkHmrBP8a8IxjgsAA7Vcy\\nzFlypZpYiuRVXln592RrsgXoSKnV5w6VN97Yqani2fAp4xVewoN9mvJXl4v4v3aN\\n5Qi/rxcAx5ZPMaCeObE0eu6MAKWJwLwYiyBV7i8eXQKBgQDX9VeUKm5hYUlAKEmR\\nK2mxQ0IiMHhUijU1lGbeArmazsGPtaWOC+lhc74GCbJ0VmWl6yKt/kixHOfaGr4o\\neif/1DGJHIiUvLzZTgbhom6GplctkLLpvrdgW6gJ6+2+E1E8KIJjamugNSMV7CkM\\n5VvMd/brlnPc5w+0c282Vg9zJQKBgQDXDP26tV6KQk73wTWWWskebE/MsA3gMK5M\\nm7UvoUyjLNlqHen7x9RkgsVSFD2wC1BwHYNc5kZ0eACyXcV8DTmWIXl98Pb03cG9\\nztM1ZZvdzQTrOQflvHQt6NgSV15QJ/oYRrw5g4o9/RG18K7lsHQt6NgSV15QJ/oY\\nRrw5g4o9/RG18K7lsH0qbcQrnxAvSLoSKa5F8nFEzwKBgQCABN6P5L9eVs+Xisph\\nljynalmP7u/GHdABHSIFxdPFI3+281Va6VDGBljFN4ZkVLsZKlR6lFz/MUV4E5Z\\naZF/F1kIvJ40HrwK8RvbpVuLySzUuu7JzwizuoCbzCrr6jHUBlnoE+Rcn95f+7Op\\nAzM4oXY0whxXUA91ZeXyZ11Z9SQKBgExTFAqcLH2toxFTxY0jk5X0oy3mnkYfgP0\\n3lkrdWLHhTRjYnR77gWpa72V+QZalrVrdXq4uHHthy/2CQoEQwIuEPfZw+3VU71p\\nKebPN6FAEX+aMSz1CcYmJxoZb8+FHDwBmuo8/HGV72DlWvvxOc14Hr0Q8JCZkDYY\\n8vNmefo0JAoGAUUtWdZ854Mo5EHmVNZcbhYoW6yXiei6McE1z4cxgcBFikDqzrX\\nM1bM9Jnh7+vL5iXO2VVDBRu2AHTViVn8tsZ1cU81RxvqXk/PgcmCecF9ik9w+Cd\\nQZj4944NP83drIIEzFtFtP0BwSzMuxo3yl4mG+sapYHQZdHV0nyT+WCVkw=\\n-----END PRIVATE KEY-----\\n"
client_email = "driver-app@drivers-481801.iam.gserviceaccount.com"
"""

# 3. เขียนไฟล์ .streamlit/secrets.toml
with open(".streamlit/secrets.toml", "w", encoding="utf-8") as f:
    f.write(secrets_content)
    print("✅ สร้างไฟล์ secrets.toml เสร็จสมบูรณ์!")
    print("🚀 ตอนนี้คุณสามารถรัน 'streamlit run app.py' ได้เลย")
