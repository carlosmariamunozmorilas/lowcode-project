/**
 * Scaling — pre-meeting intake form (automation 1, Week 4).
 *
 * Creates the Google Form a prospect fills in before the onboarding call.
 * The booking link appears only on the form's confirmation page, so the call
 * can be booked only after the form has been submitted.
 *
 * Run once from script.google.com, signed in to the account that will own the
 * form. The execution log prints the link to share and the link to edit it.
 * Most answers map onto the app's client profile (specification v2, §3):
 * products, audience, business_model, purchase_frequency,
 * avg_order_value_eur, contribution_margin, monthly_budget_eur, main_channels.
 *
 * The booking link is a placeholder here: this repository is public.
 */
const BOOKING_LINK = 'PASTE-THE-CALENDLY-LINK-HERE';

function createScalingIntakeForm() {
  const form = FormApp.create('Scaling — tell us about your store');
  form.setDescription(
    'Thank you for getting in touch with Scaling. Before our onboarding call, ' +
    'please tell us about your store. It takes about 5–8 minutes, and ranges ' +
    'and rough figures are fine. When you submit the form, you will be able ' +
    'to book a time for the call.');
  try {
    form.setEmailCollectionType(FormApp.EmailCollectionType.RESPONDER_INPUT);
  } catch (e) {
    form.setCollectEmail(true);
  }
  form.setProgressBar(true);
  form.setAllowResponseEdits(false);
  form.setShowLinkToRespondAgain(false);
  form.setConfirmationMessage(
    'Thank you — we have received your answers. ' +
    'Please book your onboarding call here: ' + BOOKING_LINK);

  // 1 · You and your store
  form.addTextItem().setTitle('Your name').setRequired(true);
  form.addTextItem().setTitle('Store or company name').setRequired(true);
  form.addTextItem().setTitle('Store website (URL)').setRequired(true);
  form.addMultipleChoiceItem()
    .setTitle('Which platform does your store run on?')
    .setChoiceValues(['Shopify', 'WooCommerce', 'PrestaShop', 'Magento / Adobe Commerce'])
    .showOtherOption(true)
    .setRequired(true);
  form.addParagraphTextItem()
    .setTitle('What do you sell?')
    .setHelpText('Your main product categories and their price range.')
    .setRequired(true);
  form.addParagraphTextItem()
    .setTitle('Who buys from you?')
    .setHelpText('Your typical customers, in a sentence or two.')
    .setRequired(true);
  form.addMultipleChoiceItem()
    .setTitle('How do you sell?')
    .setChoiceValues([
      'Our own brand, through our own online store',
      'Other brands, through our online store',
      'To other businesses (B2B)',
      'Mainly through marketplaces (Amazon, eBay, etc.)',
      'By subscription',
      'Online and in physical shops',
    ])
    .setRequired(true);
  form.addMultipleChoiceItem()
    .setTitle('How often does a typical customer buy from you?')
    .setChoiceValues(['Rarely — once a year or less', 'A few times a year', 'Monthly or more often'])
    .setRequired(true);

  // 2 · Your numbers
  form.addPageBreakItem()
    .setTitle('Your numbers')
    .setHelpText('Ranges and rough figures are fine. We will look at the real data together later.');
  form.addListItem()
    .setTitle('Online revenue in the last 12 months')
    .setChoiceValues([
      'Under €100,000', '€100,000 – €500,000', '€500,000 – €2 million',
      '€2 – €10 million', 'Over €10 million', 'Prefer not to say',
    ])
    .setRequired(true);
  form.addTextItem()
    .setTitle('Average order value (€)')
    .setHelpText('An approximate figure is fine, for example 65.')
    .setValidation(FormApp.createTextValidation()
      .setHelpText('Please enter a number, for example 65.')
      .requireNumberGreaterThan(0)
      .build())
    .setRequired(true);
  form.addMultipleChoiceItem()
    .setTitle('Roughly what is left of an order after product, shipping and payment costs?')
    .setChoiceValues(['Under 20%', '20% – 35%', '35% – 50%', 'Over 50%', "I don't know"])
    .setRequired(true);
  form.addListItem()
    .setTitle('Monthly marketing budget')
    .setChoiceValues([
      'Under €1,000', '€1,000 – €5,000', '€5,000 – €20,000', 'Over €20,000', 'Prefer not to say',
    ])
    .setRequired(true);
  form.addCheckboxItem()
    .setTitle('Where do your sales come from today?')
    .setHelpText('Tick all that apply.')
    .setChoiceValues([
      'Meta (Facebook, Instagram)', 'Google Search', 'Google Shopping', 'TikTok', 'Pinterest',
      'Email or SMS', 'Organic search (SEO)', 'Marketplaces', 'Affiliates or influencers',
    ])
    .showOtherOption(true)
    .setRequired(true);

  // 3 · Where you want to grow
  form.addPageBreakItem().setTitle('Where you want to grow');
  form.addMultipleChoiceItem()
    .setTitle('What is the main thing you want to improve in the next 6 months?')
    .setChoiceValues([
      'More new customers',
      'More visitors turning into buyers (conversion)',
      'Higher order value',
      'More repeat purchases',
      'Lower cost of acquiring customers',
      'Better margins',
      'Better measurement and reporting',
      'Automating manual work',
    ])
    .showOtherOption(true)
    .setRequired(true);
  form.addParagraphTextItem()
    .setTitle('What is holding your growth back today?')
    .setRequired(true);
  form.addParagraphTextItem()
    .setTitle('What have you already tried, and what happened?');
  form.addCheckboxItem()
    .setTitle('Which data could you share with us later?')
    .setHelpText('Only tell us what exists. We will agree a secure way to share it on the call — never send passwords.')
    .setChoiceValues([
      'Order exports from the store platform', 'Google Analytics', 'Ad accounts',
      'Email or SMS platform', 'None yet',
    ])
    .setRequired(true);
  form.addSectionHeaderItem()
    .setTitle('How we use your answers')
    .setHelpText(
      'We use your answers only to prepare our onboarding call and assess your store. ' +
      'Please do not include passwords, customer names or customer lists. ' +
      'If we do not start working together, we delete your answers after 6 months.');

  try {
    form.setPublished(true);
  } catch (e) {
    Logger.log('setPublished is not available here: ' + e);
  }
  Logger.log('Share this link: ' + form.getPublishedUrl());
  Logger.log('Edit the form: ' + form.getEditUrl());
}
