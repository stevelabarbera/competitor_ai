#!/usr/bin/env python3
"""
debug_company_keystore.py - Inspect loaded companies and aliases in keystore
"""

from company_keystore import CompanyKeystore

def inspect_keystore():
    keystore = CompanyKeystore()
    all_companies = keystore.list_all_companies()

    print(f"🏢 Total companies in keystore: {len(all_companies)}")

    for company in sorted(all_companies):
        meta = keystore.get_metadata(company)
        aliases = meta.get("aliases", [])
        tags = meta.get("tags", [])
        print(f"\n🔹 {company}")
        print(f"   Aliases: {', '.join(aliases) if aliases else 'None'}")
        print(f"   Tags: {', '.join(tags) if tags else 'None'}")

    print("\n✅ Keystore inspection complete.")

if __name__ == "__main__":
    inspect_keystore()
