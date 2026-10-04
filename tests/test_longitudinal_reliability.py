import copy
import pytest
from test_baseline_simulation import ROOT
from test_confirmed_context import record
from contextual_reference import fit_personal_reference
from longitudinal_monitoring import EWMAConfig,session_ewma
from measurement_reliability import measurement_change_reliability


def test_ewma_known_sequence_keeps_reference_frozen():
    context=record()['context']
    reference=fit_personal_reference([record(i) for i in range(5)])
    before=copy.deepcopy(reference)
    points=[{'session_id':str(i),'chronological_index':i,'context':context,'value':v,'status':'ready'}
            for i,v in enumerate([1,2,3,4])]
    result=session_ewma(points,EWMAConfig(.5,'knee_rom_rad',context))
    assert [p['ewma'] for p in result['points']]==[1,1.5,2.25,3.125]
    assert result['direction']=='increased' and result['lambda']==.5
    assert result['provenance']=='engineering_demo_smoothing_factor'
    assert result['spc_status']=='reference_limits_not_established' and result['athlete_alarm'] is None
    assert reference==before


@pytest.mark.parametrize('factor',[0,-.1,1.1,float('nan')])
def test_invalid_ewma_factor(factor):
    with pytest.raises(ValueError): EWMAConfig(factor,'knee_rom_rad',record()['context'])


def test_missing_and_wrong_context_ewma_stays_null():
    context=record()['context']
    points=[{'session_id':str(i),'chronological_index':i,'context':context,'value':v,'status':'ready'}
            for i,v in enumerate([1,None,3])]
    points[2]['context']={**context,'activity':'volleyball_training'}
    result=session_ewma(points,EWMAConfig(.3,'knee_rom_rad',context))
    assert [p['ewma'] for p in result['points']]==[1,None,None]
    assert result['status']=='unavailable'


@pytest.mark.parametrize('evidence',[None,{'mdc':.01},{'mad':.01,'sem':.01,'empirically_established':False}])
def test_missing_mdc_fails_closed(evidence):
    result=measurement_change_reliability(.8,.4,'knee_rom_rad','rad',record()['context'],evidence)
    assert result['status']=='reliability_not_established' and result['change_exceeds_mdc'] is None
    assert result['mdc'] is None


def empirical_test_fixture():
    # Contract-only injected evidence; NOT a Kintra estimate or a real empirical study.
    return {'empirically_established':True,'source':'TEST_ONLY external empirical evidence contract',
            'metric':'knee_rom_rad','unit':'rad','context':record()['context'],'mdc':.05}


@pytest.mark.parametrize('change,exceeds',[(.04,False),(.06,True)])
def test_injected_empirical_contract_and_no_injury_output(change,exceeds):
    result=measurement_change_reliability(.4+change,.4,'knee_rom_rad','rad',record()['context'],empirical_test_fixture())
    assert result['status']=='ready' and result['change_exceeds_mdc'] is exceeds
    assert not {'injury_risk','safe','unsafe','risk_probability'} & set(result)


@pytest.mark.parametrize('field',['side','activity','confirmed_movement','configuration_signature','processing_version','processing_signature'])
def test_mdc_exact_scope_required(field):
    evidence=empirical_test_fixture()
    evidence['context'][field]='different'
    result=measurement_change_reliability(.8,.4,'knee_rom_rad','rad',record()['context'],evidence)
    assert result['status']=='reliability_not_established' and result['change_exceeds_mdc'] is None
