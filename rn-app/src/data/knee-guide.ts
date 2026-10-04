// Educational illustrations, not validated anatomy or device-placement guides.
export const kneeGuide = [
  {
    title: 'How your knee works',
    description: 'Your knee bends and straightens as you move. Cartilage helps its surfaces glide, while ligaments help keep the joint stable.',
    image: require('../../assets/images/knee-how-it-works.png'),
    imageDescription: 'Illustration of a bent knee showing bones, cartilage, and ligaments.',
  },
  {
    title: 'What Kintra tracks',
    description: 'Sensors on the thigh and shin estimate how much your knee bends. Pressure insoles measure loading under your feet.',
    note: 'This prototype uses simulated data. Foot loading is not internal knee force.',
    image: require('../../assets/images/kintra-what-we-measure.png'),
    imageDescription: 'Conceptual thigh and shin sensors beside a pressure-sensing insole.',
  },
  {
    title: 'How injuries can happen',
    description: 'Sudden twisting, awkward landings, and direct impacts can injure knee structures. Repeated demands without enough recovery can also contribute to injury.',
    image: require('../../assets/images/knee-injury-mechanisms.png'),
    imageDescription: 'Athlete changing direction with a planted foot and the knee highlighted.',
  },
  {
    title: 'Help reduce injury risk',
    description: 'Warm up, build strength, and increase training gradually. Allow time for recovery and get guidance when pain persists.',
    note: 'Kintra supports movement awareness. It does not diagnose injuries or guarantee prevention.',
    image: require('../../assets/images/knee-injury-risk-reduction.png'),
    imageDescription: 'Athlete performing a bodyweight squat, with thigh muscles highlighted.',
  },
] as const;
