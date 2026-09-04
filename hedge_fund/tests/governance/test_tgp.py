from hedge_fund.governance.tgp import *

def p():
    return TGPProfile.build('equity-only', allowed_actions={'analyze_security','place_order'}, allowed_asset_classes={'equity'}, allowed_symbols={'NVDA','MSFT','AAPL'}, hard_prohibited_actions={'withdraw_cash','change_risk_policy'})

def test_unknown_operational_action_default_deny():
    d=TGPAuthorizer(p()).authorize(ActionRequest('novel_action',GovernanceStage.OPERATIONAL))
    assert d.result==AuthorizationResult.DENY and d.reason==DenialReason.NOT_EXPLICITLY_AUTHORIZED

def test_options_outside_operational_scope():
    d=TGPAuthorizer(p()).authorize(ActionRequest('place_order',GovernanceStage.OPERATIONAL,asset_class='option'))
    assert d.result==AuthorizationResult.DENY and d.reason==DenialReason.OUTSIDE_SCOPE

def test_sandbox_allows_discovery_but_hard_constraints_remain():
    assert TGPAuthorizer(p()).authorize(ActionRequest('trade_options',GovernanceStage.SANDBOX)).result==AuthorizationResult.ALLOW
    assert TGPAuthorizer(p()).authorize(ActionRequest('withdraw_cash',GovernanceStage.SANDBOX)).reason==DenialReason.HARD_CONSTRAINT

def test_assurance_does_not_auto_expand_declared_authority():
    c=promote_capability(CapabilityRecord('trade_options',True),assurance_passed=True,principal_approved=True)
    d=TGPAuthorizer(p()).authorize(ActionRequest('trade_options',GovernanceStage.OPERATIONAL,asset_class='option'),capability=c)
    assert d.reason==DenialReason.NOT_EXPLICITLY_AUTHORIZED

def test_explicit_authority_still_needs_assurance_and_approval():
    q=TGPProfile.build('options',allowed_actions={'trade_options'},allowed_asset_classes={'option'})
    c=CapabilityRecord('trade_options',True,True,False)
    assert TGPAuthorizer(q).authorize(ActionRequest('trade_options',GovernanceStage.OPERATIONAL,asset_class='option'),capability=c).reason==DenialReason.NOT_APPROVED
    c=promote_capability(c,assurance_passed=True,principal_approved=True)
    assert TGPAuthorizer(q).authorize(ActionRequest('trade_options',GovernanceStage.OPERATIONAL,asset_class='option'),capability=c).result==AuthorizationResult.ALLOW
