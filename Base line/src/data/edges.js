export const edgeData = [
  // =============== TOP PIPELINE ===============
  { id: 'e-datasets-preprocessing', source: 'datasets', target: 'preprocessing', type: 'animatedEdge' },
  { id: 'e-preprocessing-features', source: 'preprocessing', target: 'features', type: 'animatedEdge' },
  { id: 'e-features-distribution', source: 'features', target: 'distribution', type: 'animatedEdge' },

  // =============== DISTRIBUTION → VEHICLES ===============
  { id: 'e-dist-va', source: 'distribution', target: 'vehicle-a', type: 'animatedEdge' },
  { id: 'e-dist-vb', source: 'distribution', target: 'vehicle-b', type: 'animatedEdge' },
  { id: 'e-dist-vc', source: 'distribution', target: 'vehicle-c', type: 'animatedEdge' },

  // =============== VEHICLES → MAMKANFORMER ===============
  { id: 'e-va-ma', source: 'vehicle-a', target: 'mamba-a', type: 'animatedEdge' },
  { id: 'e-vb-mb', source: 'vehicle-b', target: 'mamba-b', type: 'animatedEdge' },
  { id: 'e-vc-mc', source: 'vehicle-c', target: 'mamba-c', type: 'animatedEdge' },

  // =============== MAMKANFORMER → TRAINING ===============
  { id: 'e-ma-ta', source: 'mamba-a', target: 'train-a', type: 'animatedEdge' },
  { id: 'e-mb-tb', source: 'mamba-b', target: 'train-b', type: 'animatedEdge' },
  { id: 'e-mc-tc', source: 'mamba-c', target: 'train-c', type: 'animatedEdge' },

  // =============== TRAINING → CKKS ===============
  { id: 'e-ta-ca', source: 'train-a', target: 'ckks-a', type: 'animatedEdge' },
  { id: 'e-tb-cb', source: 'train-b', target: 'ckks-b', type: 'animatedEdge' },
  { id: 'e-tc-cc', source: 'train-c', target: 'ckks-c', type: 'animatedEdge' },

  // =============== CKKS → CLOUD ===============
  { id: 'e-ca-cloud', source: 'ckks-a', target: 'cloud', type: 'animatedEdge' },
  { id: 'e-cb-cloud', source: 'ckks-b', target: 'cloud', type: 'animatedEdge' },
  { id: 'e-cc-cloud', source: 'ckks-c', target: 'cloud', type: 'animatedEdge' },

  // =============== CLOUD → BROADCAST ===============
  { id: 'e-cloud-broadcast', source: 'cloud', target: 'broadcast', type: 'animatedEdge' },

  // =============== BROADCAST → RECEIVING VEHICLES ===============
  { id: 'e-broadcast-ra', source: 'broadcast', target: 'recv-a', type: 'animatedEdge' },
  { id: 'e-broadcast-rb', source: 'broadcast', target: 'recv-b', type: 'animatedEdge' },
  { id: 'e-broadcast-rc', source: 'broadcast', target: 'recv-c', type: 'animatedEdge' },

  // =============== RECEIVING VEHICLES → IDS ===============
  { id: 'e-ra-ia', source: 'recv-a', target: 'ids-a', type: 'animatedEdge' },
  { id: 'e-rb-ib', source: 'recv-b', target: 'ids-b', type: 'animatedEdge' },
  { id: 'e-rc-ic', source: 'recv-c', target: 'ids-c', type: 'animatedEdge' },
];
