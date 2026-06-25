# REBUS variant  
  
REBUS suggests a different approach. When prediction errors spike — collisions, unexpected partner switches, persistent deadlock — the precision of existing priors should relax, and the effective learning rate should increase. The agent should update its beliefs *faster* when it discovers its model of the world is wrong.  
  
This is implementable as a dynamic learning rate parameter on the belief logits:  
  
$$\alpha_t = \alpha_{base} + k \cdot \sigma(|\text{collision}_t - \text{expected}|)$$  
  
The prediction error signal — already computed in the training loop as the cross-entropy between the belief state and the true partner type — modulates the confidence with which beliefs are updated. High surprise means high update rate. Low surprise means stable priors.  
  
Importantly, the mechanism is general. It does not depend on the presence of any pharmacological agent. It is a formal description of how a system should update its beliefs under uncertainty — applicable whether the system is a biological brain, a POMDP policy, or a multi-agent orchestrator. The psychedelic science provides the mechanistic hypothesis and the empirical parameters (Kanen et al., 2023, measured LSD's effect on prediction-error sensitivity in a computational RL model). The IRIS framework provides the testbed.  
  
The experimental design compares three conditions: a standard fixed-rate belief update, a REBUS-informed agent with precision-modulated belief update, and a combined condition in which all agents in the environment follow REBUS principles. The question is not whether REBUS works in the brain — it does. The question is whether a REBUS parameterisation of a machine learning belief update produces measurably better coordination outcomes than a fixed-rate alternative.  
  
REBUS slot-in is one line.   
  
Between belief computation and policy head, add a precision modulation:  
  
python  
```
belief = F.softmax(belief_logits, dim=-1)

# REBUS-modulated:
prediction_error = abs(collision_rate - expected_collision_rate)
alpha_t = alpha_base + k * sigmoid(prediction_error)
belief = F.softmax(alpha_t * belief_logits, dim=-1)  # precision-relaxed

```
  
And in _apply_experiment_bolt_on, add a new branch:  
  
python  
```
if self.tom_experiment == "rebus":
    # certainty-conditioned policy gating using belief entropy
    # â€” same infrastructure as belief_uncertainty_wait, but modulates
    # the partner prediction head too (dual-stream) or both agents (all-agents)

```
  
  
## What REBUS Gives Us Computationally  
  
Carhart-Harris & Friston (2019) describe REBUS as: *psychedelics relax the precision-weighting of high-level priors, allowing lower-level prediction errors to propagate upward and update beliefs faster.*  
  
This translates to three measurable, implementable parameters:  
  

| REBUS Parameter | Formal Definition | Neural Correlate (Kanen 2023/2025) |
| -------------------------------- | --------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Prediction error sensitivity (α) | Learning rate — how much a single prediction error updates the belief state | LSD increases reward-PE sensitivity quantified in computational reinforcement learning model |
| Precision relaxation (γ) | Inverse confidence in current priors — how "certain" the system is about its existing beliefs | Reduced alpha power (8–12Hz MEG/EEG); reduced DMN integrity (fMRI) |
| Belief update rate (β) | How many trials before a new observation meaningfully shifts the belief distribution | Faster reversal learning in probabilistic reward task |
  
These are not metaphors. They are parameters that can be initialised from published values and varied experimentally.  
  
## Experimental Design: REBUS in the existing Framework  
  
## Architecture Change  
  
The existing IRIS architecture uses a fixed learning rate and static belief update mechanism (train.py:397–402):  
  
```
h_t = GRU(h_{t-1}, o_t)                                     
belief_logits = W_b h_t → b_t = softmax(...)                

```
```
partner_action_logits = W_pa h_t                            
logits = W_pi[concat(h_t, b_t)]                             
logits -= safety_mask                                       
logits += _apply_decision_prior(obs, b_t, logits)           
logits += _apply_experiment_bolt_on(obs, b_t, logits)       

```
 A REBUS-informed agent adds precision modulation after belief computation and before policy head:  
```
ε_t = |collision_rate_t - expected_collision_rate|   
α_t = α_base + k * sigmoid(ε_t)   ← REBUS: prediction errors increase learning rate
b_t = softmax(α_t * W_b h_t)       ← precision-relaxed belief update

l_t = W_pi[h_t; b_t]              
    + Delta_certainty(o_t, H(b_t)) ← REBUS: high-entropy belief shifts policy weighting

```
 The specific changes are:  
1. **α_t is dynamic**, not fixed — it rises when prediction errors spike (collisions, unexpected partner switches)  
2. **Belief update is precision-weighted** — high-certainty beliefs update slowly (standard), low-certainty beliefs update fast (REBUS analogue)  
3. **Policy is certainty-conditioned** — when belief entropy is high, the agent shifts toward probing/exploration rather than committing to an action  
