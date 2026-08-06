from datetime import date

from msp.ingest.form4 import extract_ownership_xml, parse_daily_index, parse_form4

FORM4_XML = """<?xml version="1.0"?>
<ownershipDocument>
    <schemaVersion>X0508</schemaVersion>
    <documentType>4</documentType>
    <periodOfReport>2026-08-03</periodOfReport>
    <issuer>
        <issuerCik>0000320193</issuerCik>
        <issuerName>Apple Inc.</issuerName>
        <issuerTradingSymbol>aapl</issuerTradingSymbol>
    </issuer>
    <reportingOwner>
        <reportingOwnerId>
            <rptOwnerCik>0001214156</rptOwnerCik>
            <rptOwnerName>DOE JANE</rptOwnerName>
        </reportingOwnerId>
        <reportingOwnerRelationship>
            <isDirector>1</isDirector>
            <isOfficer>1</isOfficer>
            <officerTitle>Chief Executive Officer</officerTitle>
        </reportingOwnerRelationship>
    </reportingOwner>
    <nonDerivativeTable>
        <nonDerivativeTransaction>
            <securityTitle><value>Common Stock</value></securityTitle>
            <transactionDate><value>2026-08-03</value></transactionDate>
            <transactionCoding>
                <transactionFormType>4</transactionFormType>
                <transactionCode>P</transactionCode>
                <equitySwapInvolved>0</equitySwapInvolved>
            </transactionCoding>
            <transactionAmounts>
                <transactionShares><value>1000</value></transactionShares>
                <transactionPricePerShare><value>150.25</value></transactionPricePerShare>
                <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
            </transactionAmounts>
        </nonDerivativeTransaction>
    </nonDerivativeTable>
</ownershipDocument>
"""

DAILY_INDEX = """Description:           Daily Index of EDGAR Dissemination Feed by Form Type
Last Data Received:    August 3, 2026

Form Type   Company Name   CIK   Date Filed  File Name
---------------------------------------------------------------------------------
10-K        WIDGETS INC                 1111111  20260803  edgar/data/1111111/0001111111-26-000001.txt
4           APPLE INC.                  320193   20260803  edgar/data/320193/0000320193-26-000055.txt
4/A         SOMECO HOLDINGS LLC         2222222  20260803  edgar/data/2222222/0002222222-26-000002.txt
4           ACME ROBOTICS CORP          3333333  20260803  edgar/data/3333333/0003333333-26-000003.txt
"""


def test_parse_form4():
    parsed = parse_form4(FORM4_XML)
    assert parsed.issuer_cik == 320193
    assert parsed.issuer_name == "Apple Inc."
    assert parsed.issuer_ticker == "AAPL"

    assert len(parsed.owners) == 1
    owner = parsed.owners[0]
    assert owner.cik == 1214156
    assert owner.name == "DOE JANE"
    assert owner.is_director and owner.is_officer
    assert owner.officer_title == "Chief Executive Officer"

    assert len(parsed.transactions) == 1
    txn = parsed.transactions[0]
    assert txn.transaction_date == date(2026, 8, 3)
    assert txn.code == "P"
    assert txn.shares == 1000
    assert txn.price_per_share == 150.25
    assert txn.acquired_disposed == "A"


def test_parse_daily_index_filters_to_exact_form_4():
    entries = parse_daily_index(DAILY_INDEX)
    assert [e.cik for e in entries] == [320193, 3333333]
    assert entries[0].company_name == "APPLE INC."
    assert entries[0].date_filed == date(2026, 8, 3)
    assert entries[0].accession == "0000320193-26-000055"
    assert entries[0].url.endswith("edgar/data/320193/0000320193-26-000055.txt")


def test_extract_ownership_xml():
    submission = (
        "SEC-HEADER stuff\n<XML>\n<otherDoc>nope</otherDoc>\n</XML>\n"
        f"<XML>\n{FORM4_XML}\n</XML>\ntrailer"
    )
    xml = extract_ownership_xml(submission)
    assert xml is not None and "<ownershipDocument" in xml
    assert parse_form4(xml).issuer_cik == 320193


def test_extract_ownership_xml_missing():
    assert extract_ownership_xml("no xml here") is None
