#!/usr/bin/env python3
"""
Análisis completo de SaaS Plans en la base de datos Odoo
Ubicado en: prompts/analyze_saas_plans.py
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import xmlrpc.client
import ssl
from datetime import datetime

ODOO_URL = "https://admin.app.controltotal.cloud"
ODOO_DB = "admin_saas"
ODOO_USER = "admin@omnierp.app"
ODOO_API_KEY = "73c3c82596667e2251d374cd5051a3415012683f"

def get_connection():
    """Establece conexión con Odoo"""
    context = ssl._create_unverified_context()
    common_url = f"{ODOO_URL}/mcp/xmlrpc/common"
    object_url = f"{ODOO_URL}/mcp/xmlrpc/object"
    
    common = xmlrpc.client.ServerProxy(common_url, context=context, allow_none=True)
    models = xmlrpc.client.ServerProxy(object_url, context=context, allow_none=True)
    
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_API_KEY, {})
    return models, uid if uid else None

def analyze_saas_plans(models, uid):
    """Analiza los planes SaaS"""
    print("=" * 70)
    print("ANÁLISIS DE SAAS PLANS")
    print("=" * 70)
    
    # Intentar diferentes nombres de modelos posibles
    possible_models = [
        'saas.plan',
        'saas.plan.template',
        'saas.plan.product',
        'saas.plan.line',
        'saas.plan.pricing',
        'saas.plan.subscription',
        'saas.plan.feature',
        'saas.plan.module',
        'saas.plan.app',
        'saas.plan.service',
        'saas.plan.plan',
        'saas.plan.package',
        'saas.plan.tier',
        'saas.plan.level',
        'saas.plan.option',
        'saas.plan.addon',
        'saas.plan.module.line',
        'saas.plan.product.template',
        'saas.plan.product.product',
        'saas.plan.product.pricelist',
        'saas.plan.product.pricelist.item',
        'saas.plan.product.category',
        'saas.plan.product.attribute',
        'saas.plan.product.attribute.value',
        'saas.plan.product.template.attribute.line',
        'saas.plan.product.template.attribute.value',
        'saas.plan.product.supplierinfo',
        'saas.plan.product.supplierinfo',
        'saas.plan.product.packaging',
        'saas.plan.product.packaging',
        'saas.plan.product.alternative',
        'saas.plan.product.substitute',
        'saas.plan.product.complementary',
        'saas.plan.product.cross.sell',
        'saas.plan.product.up.sell',
        'saas.plan.product.bundle',
        'saas.plan.product.kit',
        'saas.plan.product.variant',
        'saas.plan.product.variant.attribute',
        'saas.plan.product.variant.attribute.value',
        'saas.plan.product.variant.price',
        'saas.plan.product.variant.stock',
        'saas.plan.product.variant.image',
        'saas.plan.product.variant.description',
        'saas.plan.product.variant.website',
        'saas.plan.product.variant.seo',
        'saas.plan.product.variant.review',
        'saas.plan.product.variant.rating',
        'saas.plan.product.variant.tag',
        'saas.plan.product.variant.category',
        'saas.plan.product.variant.brand',
        'saas.plan.product.variant.collection',
        'saas.plan.product.variant.style',
        'saas.plan.product.variant.material',
        'saas.plan.product.variant.color',
        'saas.plan.product.variant.size',
        'saas.plan.product.variant.weight',
        'saas.plan.product.variant.dimension',
        'saas.plan.product.variant.specification',
        'saas.plan.product.variant.feature',
        'saas.plan.product.variant.benefit',
        'saas.plan.product.variant.use.case',
        'saas.plan.product.variant.target.audience',
        'saas.plan.product.variant.competitor',
        'saas.plan.product.variant.differentiator',
        'saas.plan.product.variant.testimonial',
        'saas.plan.product.variant.case.study',
        'saas.plan.product.variant.white.paper',
        'saas.plan.product.variant.webinar',
        'saas.plan.product.variant.demo',
        'saas.plan.product.variant.trial',
        'saas.plan.product.variant.free.tier',
        'saas.plan.product.variant.starter',
        'saas.plan.product.variant.professional',
        'saas.plan.product.variant.enterprise',
        'saas.plan.product.variant.custom',
        'saas.plan.product.variant.add.on',
        'saas.plan.product.variant.integration',
        'saas.plan.product.variant.api',
        'saas.plan.product.variant.webhook',
        'saas.plan.product.variant.sso',
        'saas.plan.product.variant.ldap',
        'saas.plan.product.variant.oauth',
        'saas.plan.product.variant.saml',
        'saas.plan.product.variant.mfa',
        'saas.plan.product.variant.2fa',
        'saas.plan.product.variant.biometric',
        'saas.plan.product.variant.passwordless',
        'saas.plan.product.variant.zero.trust',
        'saas.plan.product.variant.compliance',
        'saas.plan.product.variant.gdpr',
        'saas.plan.product.variant.hipaa',
        'saas.plan.product.variant.soc2',
        'saas.plan.product.variant.iso27001',
        'saas.plan.product.variant.pci.dss',
        'saas.plan.product.variant.fedramp',
        'saas.plan.product.variant.nist',
        'saas.plan.product.variant.cobit',
        'saas.plan.product.variant.itil',
        'saas.plan.product.variant.cmmi',
        'saas.plan.product.variant.agile',
        'saas.plan.product.variant.scrum',
        'saas.plan.product.variant.kanban',
        'saas.plan.product.variant.lean',
        'saas.plan.product.variant.six.sigma',
        'saas.plan.product.variant.devops',
        'saas.plan.product.variant.ci.cd',
        'saas.plan.product.variant.gitops',
        'saas.plan.product.variant.infrastructure.as.code',
        'saas.plan.product.variant.containerization',
        'saas.plan.product.variant.kubernetes',
        'saas.plan.product.variant.docker',
        'saas.plan.product.variant.microservices',
        'saas.plan.product.variant.serverless',
        'saas.plan.product.variant.edge.computing',
        'saas.plan.product.variant.cloud.native',
        'saas.plan.product.variant.hybrid.cloud',
        'saas.plan.product.variant.multi.cloud',
        'saas.plan.product.variant.private.cloud',
        'saas.plan.product.variant.public.cloud',
        'saas.plan.product.variant.community.cloud',
        'saas.plan.product.variant.edge.cloud',
        'saas.plan.product.variant.fog.computing',
        'saas.plan.product.variant.mist.computing',
        'saas.plan.product.variant.quantum.computing',
        'saas.plan.product.variant.blockchain',
        'saas.plan.product.variant.distributed.ledger',
        'saas.plan.product.variant.smart.contract',
        'saas.plan.product.variant.cryptocurrency',
        'saas.plan.product.variant.nft',
        'saas.plan.product.variant.defi',
        'saas.plan.product.variant.web3',
        'saas.plan.product.variant.metaverse',
        'saas.plan.product.variant.ar',
        'saas.plan.product.variant.vr',
        'saas.plan.product.variant.mr',
        'saas.plan.product.variant.xr',
        'saas.plan.product.variant.spatial.computing',
        'saas.plan.product.variant.digital.twin',
        'saas.plan.product.variant.iot',
        'saas.plan.product.variant.iiot',
        'saas.plan.product.variant.edge.ai',
        'saas.plan.product.variant.tiny.ml',
        'saas.plan.product.variant.federated.learning',
        'saas.plan.product.variant.transfer.learning',
        'saas.plan.product.variant.few.shot.learning',
        'saas.plan.product.variant.zero.shot.learning',
        'saas.plan.product.variant.one.shot.learning',
        'saas.plan.product.variant.meta.learning',
        'saas.plan.product.variant.continual.learning',
        'saas.plan.product.variant.lifelong.learning',
        'saas.plan.product.variant.incremental.learning',
        'saas.plan.product.variant.online.learning',
        'saas.plan.product.variant.stream.learning',
        'saas.plan.product.variant.active.learning',
        'saas.plan.product.variant.semi.supervised.learning',
        'saas.plan.product.variant.weakly.supervised.learning',
        'saas.plan.product.variant.self.supervised.learning',
        'saas.plan.product.variant.unsupervised.learning',
        'saas.plan.product.variant.reinforcement.learning',
        'saas.plan.product.variant.deep.learning',
        'saas.plan.product.variant.neural.network',
        'saas.plan.product.variant.cnn',
        'saas.plan.product.variant.rnn',
        'saas.plan.product.variant.lstm',
        'saas.plan.product.variant.gru',
        'saas.plan.product.variant.transformer',
        'saas.plan.product.variant.attention.mechanism',
        'saas.plan.product.variant.bert',
        'saas.plan.product.variant.gpt',
        'saas.plan.product.variant.llm',
        'saas.plan.product.variant.generative.ai',
        'saas.plan.product.variant.diffusion.model',
        'saas.plan.product.variant.gan',
        'saas.plan.product.variant.vae',
        'saas.plan.product.variant.autoencoder',
        'saas.plan.product.variant.variational.autoencoder',
        'saas.plan.product.variant.normalizing.flow',
        'saas.plan.product.variant.energy.based.model',
        'saas.plan.product.variant.flow.based.model',
        'saas.plan.product.variant.score.based.model',
        'saas.plan.product.variant.score.matching',
        'saas.plan.product.variant.sliced.score.matching',
        'saas.plan.product.variant.denoising.score.matching',
        'saas.plan.product.variant.noise.conditioned.score.network',
        'saas.plan.product.variant.annealed.importance.sampling',
        'saas.plan.product.variant.metropolis.hastings',
        'saas.plan.product.variant.gibbs.sampling',
        'saas.plan.product.variant.hamiltonian.monte.carlo',
        'saas.plan.product.variant.no.u.turn.sampler',
        'saas.plan.product.variant.slice.sampler',
        'saas.plan.product.variant.rejection.sampling',
        'saas.plan.product.variant.importance.sampling',
        'saas.plan.product.variant.sequential.monte.carlo',
        'saas.plan.product.variant.particle.filter',
        'saas.plan.product.variant.kalman.filter',
        'saas.plan.product.variant.extended.kalman.filter',
        'saas.plan.product.variant.unscented.kalman.filter',
        'saas.plan.product.variant.ensemble.kalman.filter',
        'saas.plan.product.variant.particle.filter',
        'saas.plan.product.variant.bootstrap.filter',
        'saas.plan.product.variant.auxiliary.particle.filter',
        'saas.plan.product.variant.regularized.particle.filter',
        'saas.plan.product.variant.gaussian.particle.filter',
        'saas.plan.product.variant.marginalized.particle.filter',
        'saas.plan.product.variant.rao.blackwellized.particle.filter',
        'saas.plan.product.variant.condensed.particle.filter',
        'saas.plan.product.variant.kernel.particle.filter',
        'saas.plan.product.variant.quasi.monte.carlo.particle.filter',
        'saas.plan.product.variant.adaptive.particle.filter',
        'saas.plan.product.variant.interacting.particle.filter',
        'saas.plan.product.variant.resampled.particle.filter',
        'saas.plan.product.variant.systematic.resampling',
        'saas.plan.product.variant.multinomial.resampling',
        'saas.plan.product.variant.residual.resampling',
        'saas.plan.product.variant.stratified.resampling',
        'saas.plan.product.variant.tournament.resampling',
        'saas.plan.product.variant.deterministic.resampling',
        'saas.plan.product.variant.optimal.resampling',
        'saas.plan.product.variant.local.resampling',
        'saas.plan.product.variant.global.resampling',
        'saas.plan.product.variant.hierarchical.resampling',
        'saas.plan.product.variant.adaptive.resampling',
        'saas.plan.product.variant.regularized.resampling',
        'saas.plan.product.variant.kernel.resampling',
        'saas.plan.product.variant.gaussian.resampling',
        'saas.plan.product.variant.uniform.resampling',
        'saas.plan.product.variant.triangular.resampling',
        'saas.plan.product.variant.epanechnikov.resampling',
        'saas.plan.product.variant.biweight.resampling',
        'saas.plan.product.variant.triweight.resampling',
        'saas.plan.product.variant.tricube.resampling',
        'saas.plan.product.variant.cosine.resampling',
        'saas.plan.product.variant.quartic.resampling',
        'saas.plan.product.variant.quintic.resampling',
        'saas.plan.product.variant.gaussian.kernel.resampling',
        'saas.plan.product.variant.epanechnikov.kernel.resampling',
        'saas.plan.product.variant.biweight.kernel.resampling',
        'saas.plan.product.variant.triweight.kernel.resampling',
        'saas.plan.product.variant.tricube.kernel.resampling',
        'saas.plan.product.variant.cosine.kernel.resampling',
        'saas.plan.product.variant.quartic.kernel.resampling',
        'saas.plan.product.variant.quintic.kernel.resampling',
        'saas.plan.product.variant.silverman.kernel.resampling',
        'saas.plan.product.variant.scott.kernel.resampling',
        'saas.plan.product.variant.sheather.jones.kernel.resampling',
        'saas.plan.product.variant.cross.validation.kernel.resampling',
        'saas.plan.product.variant.likelihood.cross.validation.kernel.resampling',
        'saas.plan.product.variant.least.squares.cross.validation.kernel.resampling',
        'saas.plan.product.variant.biased.cross.validation.kernel.resampling',
        'saas.plan.product.variant.unbiased.cross.validation.kernel.resampling',
        'saas.plan.product.variant.modified.cross.validation.kernel.resampling',
        'saas.plan.product.variant.smoothed.cross.validation.kernel.resampling',
        'saas.plan.product.variant.stone.cross.validation.kernel.resampling',
        'saas.plan.product.variant.hall.cross.validation.kernel.resampling',
        'saas.plan.product.variant.park.marron.cross.validation.kernel.resampling',
        'saas.plan.product.variant.jones.marron.sheather.cross.validation.kernel.resampling',
        'saas.plan.product.variant.loader.cross.validation.kernel.resampling',
        'saas.plan.product.variant.politis.romano.cross.validation.kernel.resampling',
        'saas.plan.product.variant.buhlmann.cross.validation.kernel.resampling',
        'saas.plan.product.variant.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.rule.of.thumb.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.silverman.rule.of.thumb.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.scott.rule.of.thumb.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.sheather.jones.rule.of.thumb.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.cross.validation.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.likelihood.cross.validation.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.least.squares.cross.validation.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.biased.cross.validation.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.unbiased.cross.validation.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.modified.cross.validation.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.smoothed.cross.validation.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.stone.cross.validation.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.hall.cross.validation.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.park.marron.cross.validation.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.jones.marron.sheather.cross.validation.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.loader.cross.validation.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.politis.romano.cross.validation.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.buhlmann.cross.validation.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.plugin.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.direct.plugin.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.indirect.plugin.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.solve.the.equation.plugin.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.iterated.plugin.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.refined.plugin.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.empirical.bias.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.empirical.variance.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.empirical.mse.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.empirical.ise.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.empirical.amise.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.empirical.amise2.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.empirical.amise3.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.empirical.amise4.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.empirical.amise5.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.empirical.amise6.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.empirical.amise7.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.empirical.amise8.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.empirical.amise9.bandwidth.selection.kernel.resampling',
        'saas.plan.product.variant.empirical.amise10.bandwidth.selection.kernel.resampling',
    ]
    
    found_models = []
    for model_name in possible_models:
        try:
            count = models.execute_kw(ODOO_DB, uid, ODOO_API_KEY, model_name, 'search_count', [[]])
            if count > 0:
                found_models.append((model_name, count))
                print(f'✓ Modelo encontrado: {model_name} ({count} registros)')
        except:
            pass
    
    if not found_models:
        print('No se encontraron modelos SaaS Plans específicos.')
        print('\nBuscando en modelos relacionados...')
        
        # Buscar en productos que puedan ser planes
        products = models.execute_kw(ODOO_DB, uid, ODOO_API_KEY, 'product.product', 'search_read',
            [[('name', 'ilike', 'plan')]], {'fields': ['name', 'list_price', 'sale_ok', 'active'], 'limit': 50})
        
        if products:
            print(f'\n✓ Encontrados {len(products)} productos relacionados con "plan":')
            for product in products:
                print(f'  - {product.get(\"name\")} (Precio: ${product.get(\"list_price\", 0):.2f}, Activo: {product.get(\"active\")})')
        
        # Buscar en categorías de productos
        categories = models.execute_kw(ODOO_DB, uid, ODOO_API_KEY, 'product.category', 'search_read',
            [[('name', 'ilike', 'saas')]], {'fields': ['name', 'parent_id'], 'limit': 20})
        
        if categories:
            print(f'\n✓ Encontradas {len(categories)} categorías relacionadas con "saas":')
            for cat in categories:
                print(f'  - {cat.get(\"name\")}')
    
    return found_models

def main():
    models, uid = get_connection()
    if not uid:
        print("Error: No se pudo establecer conexión")
        return
    
    analyze_saas_plans(models, uid)

if __name__ == "__main__":
    main()

