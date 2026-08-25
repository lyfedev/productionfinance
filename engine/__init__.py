"""ProductionFinance incentive engine.

A generic, data-driven interpreter for jurisdiction production-incentive
rules. Every jurisdiction is a data file under ``jurisdictions/*.yaml``,
validated against ``engine.models.JurisdictionRuleSet``; nothing in this
package is named for, or branches on, a jurisdiction identifier string
(Phase 2's JUR-05 requirement). See ``jurisdictions/SCOPE-FREEZE.md`` for the
dated boundary of what a rule file may express.
"""

__version__ = "0.1.0"
